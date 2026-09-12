package config

type HierShrinkSelectionConfig struct {
	ArtifactPath       string  `yaml:"artifact_path"`
	EmbeddingModel     string  `yaml:"embedding_model"`
	EmbeddingDimension int     `yaml:"embedding_dimension"`
	CostWeight         float64 `yaml:"cost_weight,omitempty"`
}
