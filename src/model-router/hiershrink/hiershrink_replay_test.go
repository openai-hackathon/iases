package selection

import (
	"encoding/json"
	"math"
	"os"
	"testing"

	"github.com/vllm-project/semantic-router/src/semantic-router/pkg/config"
)

type hierShrinkReplay struct {
	Artifact  string
	Dimension int
	Cases     []struct {
		Embedding  []float32
		Candidates []string
		Weight     float64
		Model      string
		Scores     map[string]float64
	}
}

func TestHierShrinkReferenceReplay(t *testing.T) {
	path := os.Getenv("HIERSHRINK_REPLAY")
	if path == "" {
		t.Skip("set HIERSHRINK_REPLAY to a Python reference replay file")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var profiles []hierShrinkReplay
	if err := json.Unmarshal(data, &profiles); err != nil {
		t.Fatal(err)
	}
	count, maximumError := 0, 0.0
	for _, profile := range profiles {
		for _, example := range profile.Cases {
			selector := NewHierShrinkSelector(config.HierShrinkSelectionConfig{ArtifactPath: profile.Artifact, EmbeddingModel: "reference-encoder", EmbeddingDimension: profile.Dimension, CostWeight: example.Weight}, nil)
			request := &SelectionContext{QueryEmbedding: example.Embedding}
			for _, model := range example.Candidates {
				request.CandidateModels = append(request.CandidateModels, config.ModelRef{Model: model})
			}
			result, err := selector.Select(t.Context(), request)
			if err != nil {
				t.Fatal(err)
			}
			if result.SelectedModel != example.Model {
				t.Fatalf("model mismatch: %s != %s", result.SelectedModel, example.Model)
			}
			for model, expected := range example.Scores {
				maximumError = math.Max(maximumError, math.Abs(result.AllScores[model]-expected))
				if maximumError > 1e-6 {
					t.Fatalf("utility mismatch: %.9g", maximumError)
				}
			}
			count++
		}
	}
	if count == 0 {
		t.Fatal("empty reference replay")
	}
	t.Logf("%d selections match Python; max utility error %.9g", count, maximumError)
}

func BenchmarkHierShrinkProfile(b *testing.B) {
	path := os.Getenv("HIERSHRINK_REPLAY")
	if path == "" {
		b.Skip("set HIERSHRINK_REPLAY")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		b.Fatal(err)
	}
	var profiles []hierShrinkReplay
	if err := json.Unmarshal(data, &profiles); err != nil {
		b.Fatal(err)
	}
	for _, profile := range profiles {
		b.Run(profile.Artifact, func(b *testing.B) {
			example := profile.Cases[0]
			selector := NewHierShrinkSelector(config.HierShrinkSelectionConfig{ArtifactPath: profile.Artifact, EmbeddingModel: "reference-encoder", EmbeddingDimension: profile.Dimension, CostWeight: example.Weight}, nil)
			request := &SelectionContext{QueryEmbedding: example.Embedding}
			for _, model := range example.Candidates {
				request.CandidateModels = append(request.CandidateModels, config.ModelRef{Model: model})
			}
			b.ResetTimer()
			for b.Loop() {
				if _, err := selector.Select(b.Context(), request); err != nil {
					b.Fatal(err)
				}
			}
		})
	}
}
