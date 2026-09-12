package extproc

import (
	"fmt"
	"sync"

	"github.com/vllm-project/semantic-router/src/semantic-router/pkg/config"
	"github.com/vllm-project/semantic-router/src/semantic-router/pkg/selection"
)

func (router *OpenAIRouter) hierShrinkSelector(cfg *config.HierShrinkSelectionConfig) selection.Selector {
	create := sync.OnceValue(func() selection.Selector {
		embed, embeddingConfig := resolveSelectionEmbeddingFunc(router.Config)
		encoder := embeddingConfig.ModelType
		if encoder == config.EmbeddingModelTypeRemote {
			encoder = router.Config.EmbeddingModels.Endpoint.Model
		}
		return selection.NewHierShrinkSelector(*cfg, func(query string) ([]float32, error) {
			if encoder != cfg.EmbeddingModel || embeddingConfig.TargetDimension != cfg.EmbeddingDimension {
				return nil, fmt.Errorf("HierShrink encoder does not match the router embedding configuration")
			}
			return embed(query, embeddingConfig)
		})
	})
	actual, _ := router.hierShrinkSelectors.LoadOrStore(*cfg, create)
	return actual.(func() selection.Selector)()
}
