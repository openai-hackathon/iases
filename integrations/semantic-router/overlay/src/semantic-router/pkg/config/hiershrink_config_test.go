package config

import (
	"math"
	"testing"

	"gopkg.in/yaml.v2"
)

func TestHierShrinkConfig(t *testing.T) {
	var algorithm AlgorithmConfig
	if err := yaml.Unmarshal([]byte("type: hiershrink\nhiershrink:\n  artifact_path: profile.json\n  embedding_model: bge\n  embedding_dimension: 768\n  cost_weight: 0.1\n"), &algorithm); err != nil {
		t.Fatal(err)
	}
	if err := validateSpecializedAlgorithmConfig("incident", nil, algorithm.Type, &algorithm); err != nil {
		t.Fatal(err)
	}
	for _, cfg := range []*HierShrinkSelectionConfig{
		nil, {}, {ArtifactPath: "profile.json", EmbeddingModel: "bge", EmbeddingDimension: 0},
		{ArtifactPath: "profile.json", EmbeddingModel: "bge", EmbeddingDimension: 768, CostWeight: math.NaN()},
		{ArtifactPath: "profile.json", EmbeddingModel: "bge", EmbeddingDimension: 768, CostWeight: -1},
	} {
		algorithm.HierShrink = cfg
		if err := validateSpecializedAlgorithmConfig("incident", nil, algorithm.Type, &algorithm); err == nil {
			t.Fatalf("accepted %v", cfg)
		}
	}
}
