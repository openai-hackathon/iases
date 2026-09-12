import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from aligned_embedllm import historical_strength
from audit.estimators import assign_hierarchy, cluster_table, empirical_strength, fit_clusters, fit_hierarchy
from research40.serving import fit_router, predict_router, query_features
from uniroute_paper_cpu import ROOT, load_data, metric
from uniroute_paper_report import check_prediction


def load_case(dataset, seed):
    directory=ROOT/'results/uniroute_text_cpu'/dataset/str(seed)
    protocol=dict(np.load(directory/'protocol.npz'))
    x,scores,costs,eligible,audit,hashes=load_data(dataset,'text')
    x=F.normalize(x,dim=1)
    a={name:torch.from_numpy(protocol[name]) for name in ('train','val','test','train_models','test_models','observed')}
    centers={k:torch.from_numpy(np.load(directory/f'hierarchy_centers_{k}.npy')) for k in (20,100)}
    labels={k:(x @ center.T).argmax(1) for k,center in centers.items()}
    parents=torch.tensor([torch.bincount(labels[20][a['train']][labels[100][a['train']]==c],minlength=20).argmax() for c in range(100)])
    assert torch.equal(scores[a['test']][:,a['test_models']],torch.from_numpy(protocol['quality']))
    return directory,x,scores,costs,a,centers,labels,parents


def reference_predictions(x, quality, support, targets, neighbors=30):
    result=torch.zeros(len(x),quality.shape[1])
    for ids in targets.split(256):
        nearest=(x[ids] @ x[support].T).topk(neighbors,dim=1).indices
        result[ids]=quality[support][nearest].mean(1)
    return result


def nested_partition(x, train, coarse, seed):
    children=fit_hierarchy(x[train],coarse,seed)
    labels={20:(x @ coarse.T).argmax(1),100:assign_hierarchy(x,coarse,children)}
    return labels,torch.arange(100)//5,children.flatten(0,1)


def fit_prior(reference, quality, tau=.02):
    distance=(reference[:,:,None]-quality[:,None,:]).square().mean(0)
    weights=(-distance/tau).softmax(0)
    offset=quality.mean(0)-(reference @ weights).mean(0)
    return dict(weights=weights,offset=offset)


def predict_prior(state, reference):
    return reference @ state['weights']+state['offset']


def fit_profile(reference, labels, quality, strength, parents, level=None, tau=.02):
    state=fit_prior(reference,quality,tau)
    residual=quality-reference @ state['weights']-state['offset']
    root=residual.mean(0,keepdim=True)
    coarse_ids=torch.arange(20)
    _,coarse=cluster_table(labels[20],residual,coarse_ids,20,root,strength[20])
    _,fine=cluster_table(labels[100],residual,torch.arange(100),100,root,strength[100],coarse[parents])
    return dict(**state,table=coarse if level==20 else fine,level=20 if level==20 else 100)


def predict_profile(state, features):
    return predict_prior(state,features['reference'])+state['table'][features['labels'][state['level']]]


def leave_one_out_prior(reference, quality, observed, target):
    distance=(reference[observed,:,None]-quality[observed,None,:]).square().mean(0)
    distance.fill_diagonal_(float('inf'))
    weights=(-distance/.02).softmax(0)
    offset=quality[observed].mean(0)-(reference[observed] @ weights).mean(0)
    return reference[target] @ weights+offset


def residual_strength(labels, residual, parents):
    means,variances,counts={},{},{}
    for k in (20,100):
        counts[k]=torch.bincount(labels[k],minlength=k)[:,None]
        sums=torch.zeros(k,residual.shape[1]).index_add_(0,labels[k],residual)
        squares=torch.zeros_like(sums).index_add_(0,labels[k],residual.square())
        means[k]=sums/counts[k].clamp_min(1)
        variances[k]=((squares-sums.square()/counts[k].clamp_min(1))/(counts[k]-1).clamp_min(1)).clamp_min(0)
    strength={}
    for k in (20,100):
        parent=torch.zeros_like(means[k]) if k==20 else means[20][parents]
        noise=variances[k].mean(1)
        mismatch=(means[k]-parent).square().mean(1)
        strength[k]=(noise/mismatch.clamp_min(1e-4)).clamp(3,300)
        strength[k][counts[k].squeeze(1)<2]=300
    return strength


def calibrate(x, quality, costs, train, val, labels, nested, parents, nested_parents, seed):
    order=train[torch.from_numpy(np.random.default_rng(seed+44000).permutation(len(train)))]
    support=order[:int(.8*len(order))]
    calibration=order[len(support):]
    observed=calibration[:200]
    moments=calibration[200:]
    reference=reference_predictions(x,quality,support,torch.cat([calibration,val]))
    strengths={name:{k:[] for k in (20,100)} for name in ('residual','nested_residual')}
    choices=(3,10,30,100,300)
    values={alpha:[] for alpha in choices}
    for budget in (60,200):
        obs=observed[:budget]
        target=torch.cat([obs,moments,val])
        prior=leave_one_out_prior(reference,quality,obs,target)
        fitted,residual_pred,test_prior=torch.split(prior,[budget,len(moments),len(val)])
        residual=quality[moments]-residual_pred
        for name,assignment,parent in [('residual',labels,parents),('nested_residual',nested,nested_parents)]:
            fitted_strength=residual_strength({k:v[moments] for k,v in assignment.items()},residual,parent)
            for k,value in fitted_strength.items():
                strengths[name][k].append(value)
        y=quality[obs]-fitted
        for alpha in choices:
            fixed=torch.tensor(float(alpha))
            _,coarse=cluster_table(labels[20][obs],y,torch.arange(20),20,y.mean(0,keepdim=True),fixed)
            prediction,_=cluster_table(labels[100][obs],y,labels[100][val],100,y.mean(0,keepdim=True),fixed,coarse[parents])
            values[alpha].append(metric(test_prior+prediction,quality[val],costs)['area'])
    selected=max(choices,key=lambda value:np.mean(values[value]))
    return {name:{k:torch.stack(v).mean(0) for k,v in row.items()} for name,row in strengths.items()},dict(
        fixed_alpha=selected,validation_areas=values,support=support.tolist(),observed=observed.tolist(),moments=moments.tolist())


def tensor_bytes(value):
    if isinstance(value,torch.Tensor):
        return value.numel()*value.element_size()
    if isinstance(value,dict):
        return sum(tensor_bytes(v) for v in value.values())
    if isinstance(value,(list,tuple)):
        return sum(tensor_bytes(v) for v in value)
    return 0


def measure(function, repeats=7):
    function()
    samples=[]
    for _ in range(repeats):
        started=time.perf_counter()
        function()
        samples.append(time.perf_counter()-started)
    return dict(median_seconds=float(np.median(samples)),p95_seconds=float(np.quantile(samples,.95)),samples=samples)


def record_prediction(output, name, value, truth, costs, metadata):
    result=metric(value,truth,costs)
    row=dict(**metadata,method=name,**{key:result[key] for key in ('area','area50','qnc','reached_best','brier','best_single_accuracy','best_single_cost')})
    row['verification_error']=check_prediction(value.detach().numpy(),truth.numpy().astype(np.float64),costs,result,row)
    filename=f'{metadata["budget"]}_{name}.npz'
    np.savez_compressed(output/filename,prediction=value.detach().numpy(),curve_cost=np.asarray(result['cost']),curve_quality=np.asarray(result['accuracy']))
    return row


@torch.no_grad()
def run(dataset,seed):
    torch.set_num_threads(4)
    output=ROOT/'results/final_closed_cpu'/dataset/str(seed)
    output.mkdir(parents=True,exist_ok=True)
    if (output/'complete.json').exists():
        return
    started=time.monotonic()
    source,x,scores,costs,a,centers,labels,parents=load_case(dataset,seed)
    construction=scores[:,a['train_models']]
    then=time.perf_counter()
    nested,nested_parents,nested_centers=nested_partition(x,a['train'],centers[20],seed+50000)
    nested_seconds=time.perf_counter()-then
    then=time.perf_counter()
    for k in (20,100):
        fit_clusters(x[a['train']],k,seed+k)
    geometry_seconds=time.perf_counter()-then
    strength=historical_strength(labels,a['train'],construction[a['train']])
    nested_strength=historical_strength(nested,a['train'],construction[a['train']])
    calibrated,tuning=calibrate(x,construction,costs[a['train_models']],a['train'],a['val'],labels,nested,parents,nested_parents,seed)
    recipes={
        'ungated':(labels,parents,strength,None),
        'single20_ungated':(labels,parents,strength,20),
        'nested':(nested,nested_parents,nested_strength,None),
        'residual':(labels,parents,calibrated['residual'],None),
        'nested_residual':(nested,nested_parents,calibrated['nested_residual'],None),
        'fixed':(labels,parents,{k:torch.full((k,),float(tuning['fixed_alpha'])) for k in (20,100)},None)}
    then=time.perf_counter()
    reference=reference_predictions(x,construction,a['train'],torch.cat([a['val'],a['test']]))
    reference_seconds=time.perf_counter()-then
    truth=scores[a['test']][:,a['test_models']]
    protocol=dict(np.load(source/'protocol.npz'))
    np.savez_compressed(output/'protocol.npz',**protocol,nested_centers=nested_centers.numpy(),nested_labels=nested[100].numpy())
    (output/'tuning.json').write_text(json.dumps(tuning,indent=2)+'\n')
    records,performance,distributions,archive_parity=[],[],[],[]
    for name,(_,_,weights,_) in recipes.items():
        for k,v in weights.items():
            distributions.append(dict(method=name,resolution=k,values=v.tolist(),q05=float(v.quantile(.05)),median=float(v.median()),q95=float(v.quantile(.95)),at_lower=float((v<=3).float().mean()),at_upper=float((v>=300).float().mean())))
    budgets=json.loads((source/'protocol.json').read_text())['budgets']
    shared=dict(strength={k:empirical_strength(labels[k][a['train']],construction[a['train']],k,construction[a['train']].mean(0)) for k in labels})
    for budget in budgets:
        observed=a['observed'][:budget]
        quality=scores[observed][:,a['test_models']]
        metadata=dict(dataset=dataset,seed=seed,budget=budget)
        for name,(assignment,parent,weights,level) in recipes.items():
            state=fit_profile(reference[observed],{k:v[observed] for k,v in assignment.items()},quality,weights,parent,level)
            features=dict(reference=reference[a['test']],labels={k:v[a['test']] for k,v in assignment.items()})
            prediction=predict_profile(state,features)
            if name=='ungated':
                old=torch.from_numpy(np.load(source/f'predictions_{budget}.npz')['no_gate'])
                error=float((prediction-old).abs().max())
                area_difference=metric(prediction,truth,costs[a['test_models']])['area']-metric(old,truth,costs[a['test_models']])['area']
                assert abs(area_difference)<1e-4,(error,area_difference)
                archive_parity.append(dict(budget=budget,method=name,max_prediction_difference=error,area_difference=area_difference))
            records.append(record_prediction(output,name,prediction,truth,costs[a['test_models']],metadata))
        if budget in (60,200,500,len(a['val'])):
            observed_features=dict(reference=reference[observed],labels={k:v[observed] for k,v in labels.items()})
            target_ids=a['test'][:256]
            target_features=dict(reference=reference[target_ids],labels={k:v[target_ids] for k,v in labels.items()})
            fitters={
                'ungated':lambda:fit_profile(reference[observed],observed_features['labels'],quality,strength,parents),
                'flat':lambda:fit_router('flat_split_uniform',x[observed],quality,observed_features,None,shared)}
            for name,fit in fitters.items():
                state=fit()
                predict=(lambda:predict_profile(state,target_features)) if name=='ungated' else (lambda:predict_router(state,x[target_ids],target_features))
                if name=='ungated':
                    saved=torch.from_numpy(np.load(output/f'{budget}_ungated.npz')['prediction'])[:len(target_ids)]
                else:
                    full_features=dict(reference=reference[a['test']],labels={k:v[a['test']] for k,v in labels.items()})
                    full_prediction=predict_router(state,x[a['test']],full_features)
                    saved=full_prediction[:len(target_ids)]
                    old=torch.from_numpy(np.load(source/f'predictions_{budget}.npz')['flat'])
                    archive_parity.append(dict(budget=budget,method=name,max_prediction_difference=float((full_prediction-old).abs().max()),
                        area_difference=metric(full_prediction,truth,costs[a['test_models']])['area']-metric(old,truth,costs[a['test_models']])['area']))
                torch.testing.assert_close(predict().clamp(0,1),saved.clamp(0,1),atol=3e-6,rtol=3e-6)
                performance.append(dict(**metadata,method=name,models=len(a['test_models']),queries=len(target_ids),fit=measure(fit,5),predict=measure(predict),state_bytes=tensor_bytes(state),observed_score_cells=budget*len(a['test_models'])))
            serving=dict(embeddings=x[a['train']],scores=construction[a['train']],centers=centers)
            performance.append(dict(**metadata,method='shared_features',queries=len(target_ids),predict=measure(lambda:query_features(serving,x[target_ids])),state_bytes=tensor_bytes(serving)))
        (output/'report.json').write_text(json.dumps(dict(records=records,performance=performance,strengths=distributions,
            reference_seconds=reference_seconds,nested_fit_seconds=nested_seconds,geometry_fit_seconds=geometry_seconds,
            reference_score_cells=len(a['train'])*len(a['train_models']),archive_parity=archive_parity,
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
        print(json.dumps(dict(dataset=dataset,seed=seed,budget=budget,seconds=time.monotonic()-started)),flush=True)
    (output/'complete.json').write_text(json.dumps(dict(records=len(records),seconds=time.monotonic()-started))+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('dataset',choices=('embedllm','routerbench'))
    parser.add_argument('seed',type=int)
    args=parser.parse_args()
    run(args.dataset,args.seed)
