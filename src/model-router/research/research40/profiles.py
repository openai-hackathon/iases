"""Reference-profile episode with no cluster fitting and no neural training."""

import json
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from audit.estimators import smooth_reference
from audit.protocol import digest
from .grouping import make_group_split,observation_order


class ProfileEpisode:
    def __init__(self,arrays,seed):
        self.seed=seed
        self.groups=arrays["groups"]
        split=make_group_split(self.groups,seed+420000)
        split={name:observation_order(ids,self.groups,seed+610000+j)
               for j,(name,ids) in enumerate(split.items())}
        models=np.random.default_rng(seed).permutation(arrays["scores"].shape[1])
        split.update(train_m=models[:62],tune_m=models[62:74],test_m=models[74:])
        self.split=split
        device="cuda" if torch.cuda.is_available() else "cpu"
        self.idx={name:torch.tensor(ids,device=device) for name,ids in split.items()}
        self.x=F.normalize(torch.tensor(arrays["embeddings"],device=device),dim=1)
        self.y=torch.tensor(arrays["scores"],device=device)
        self.cost=torch.tensor(arrays["costs"],device=device,dtype=torch.float32)
        tq,tm=self.idx["train_q"],self.idx["train_m"]
        self.reference=smooth_reference(self.x,tq,self.y[tq][:,tm])

    def observations(self,k,draw):
        ids=observation_order(self.split["obs_q"],self.groups,self.seed+10000+draw)[:k]
        if len(ids)!=k:
            raise ValueError("Insufficient distinct onboarding groups")
        return torch.tensor(ids,device=self.x.device)


def setup(seed,folder,parent_file,round_id,episode_class=ProfileEpisode):
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.manual_seed(seed)
    arrays=dict(np.load(Path(folder)/"data.npz"))
    result=json.loads(Path(parent_file).read_text())
    assert digest(arrays["scores"])==result["data"]["score_sha256"]
    assert digest(arrays["embeddings"])==result["data"]["embedding_sha256"]
    ep=episode_class(arrays,seed)
    assert result["split"]=={name:ids.tolist() for name,ids in ep.split.items()}
    parent=result["round"].lower()
    result[f"{parent}_code_sha256"]=result.pop("code_sha256")
    result[f"{parent}_seconds"]=result.pop("seconds")
    result["round"]=round_id
    return ep,result


def verify_observation(result,obs,k,draw):
    expected=next(r["ids"] for r in result["observations"] if r["k"]==k and r["draw"]==draw)
    assert expected==obs.cpu().tolist()
