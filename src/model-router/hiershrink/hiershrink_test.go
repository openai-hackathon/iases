package selection

import (
	"context"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/vllm-project/semantic-router/src/semantic-router/pkg/config"
)

func hierShrinkFixture(testingContext testing.TB) config.HierShrinkSelectionConfig {
	testingContext.Helper()
	artifact := hierShrinkArtifact{
		Version: 1, Encoder: "fixture", Models: []string{"strong", "cheap"}, Costs: []float64{1, 0.1},
		Layers: []hierShrinkLayer{
			{Weights: [][]float64{{1, 0}, {0, 1}}, Bias: []float64{0, 0}},
			{Weights: [][]float64{{1, 0}, {0, 1}}, Bias: []float64{0, 0}},
			{Weights: [][]float64{{1, 0}, {0, 1}}, Bias: []float64{0, 0}},
		},
		Profile: [][]float64{{0.8, 0.4}, {0.6, 0.7}}, Offset: []float64{0.05, 0},
		Table: [][]float64{{0.02, -0.01}, {-0.1, 0.1}}, Centers: [][]float64{{1, 0}, {0, 1}},
	}
	encoded, err := json.Marshal(artifact)
	if err != nil {
		testingContext.Fatal(err)
	}
	path := filepath.Join(testingContext.TempDir(), "profile.json")
	if err := os.WriteFile(path, encoded, 0600); err != nil {
		testingContext.Fatal(err)
	}
	return config.HierShrinkSelectionConfig{ArtifactPath: path, EmbeddingModel: "fixture", EmbeddingDimension: 2}
}

func TestHierShrinkSelection(t *testing.T) {
	cfg := hierShrinkFixture(t)
	request := &SelectionContext{QueryEmbedding: []float32{1, 0}, CandidateModels: []config.ModelRef{{Model: "strong"}, {Model: "cheap", LoRAName: "adapter"}}}
	selector := NewHierShrinkSelector(cfg, nil)
	result, err := selector.Select(t.Context(), request)
	if err != nil {
		t.Fatal(err)
	}
	probability := math.Exp(1) / (math.Exp(1) + 1)
	expected := &SelectionResult{SelectedModel: "strong", Score: probability*0.8 + (1-probability)*0.6 + 0.07, Method: MethodHierShrink, Tier: TierExperimental, AllScores: map[string]float64{"strong": probability*0.8 + (1-probability)*0.6 + 0.07, "cheap": probability*0.4 + (1-probability)*0.7 - 0.01}, Reasoning: "Predicted quality minus weighted artifact cost; not calibrated confidence"}
	if math.Abs(result.Score-expected.Score) > 1e-12 {
		t.Fatalf("score: got %v want %v", result, expected)
	}
	for model, score := range expected.AllScores {
		if math.Abs(result.AllScores[model]-score) > 1e-12 {
			t.Fatalf("scores: %v", result.AllScores)
		}
	}
	result.Score, result.AllScores = expected.Score, expected.AllScores
	if !reflect.DeepEqual(result, expected) {
		t.Fatalf("got %#v want %#v", result, expected)
	}
	cfg.CostWeight = 1
	result, err = NewHierShrinkSelector(cfg, nil).Select(t.Context(), request)
	if err != nil || result.SelectedModel != "cheap" || result.LoRAName != "adapter" {
		t.Fatalf("cost selection: %v %v", result, err)
	}
	request.CandidateModels = request.CandidateModels[:1]
	result, err = NewHierShrinkSelector(cfg, nil).Select(t.Context(), request)
	if err != nil || result.SelectedModel != "strong" {
		t.Fatalf("candidate restriction: %v %v", result, err)
	}
	if selector.UpdateFeedback(t.Context(), &Feedback{}) == nil {
		t.Fatal("online feedback must be rejected")
	}
}

func TestHierShrinkValidation(t *testing.T) {
	cfg := hierShrinkFixture(t)
	selector := NewHierShrinkSelector(cfg, nil)
	for _, embedding := range [][]float32{nil, {1}, {0, 0}, {float32(math.NaN()), 0}} {
		_, err := selector.Select(t.Context(), &SelectionContext{QueryEmbedding: embedding, CandidateModels: []config.ModelRef{{Model: "strong"}}})
		if err == nil {
			t.Fatalf("accepted embedding %v", embedding)
		}
	}
	_, err := selector.Select(t.Context(), &SelectionContext{QueryEmbedding: []float32{1, 0}, CandidateModels: []config.ModelRef{{Model: "unknown"}}})
	if err == nil {
		t.Fatal("accepted unknown backend")
	}
	for _, mutate := range []func(*config.HierShrinkSelectionConfig){
		func(value *config.HierShrinkSelectionConfig) { value.EmbeddingModel = "wrong" },
		func(value *config.HierShrinkSelectionConfig) { value.ArtifactPath += ".missing" },
		func(value *config.HierShrinkSelectionConfig) { value.CostWeight = -1 },
		func(value *config.HierShrinkSelectionConfig) { value.EmbeddingDimension = 3 },
	} {
		changed := cfg
		mutate(&changed)
		if NewHierShrinkSelector(changed, nil).loadError == nil {
			t.Fatal("accepted invalid configuration")
		}
	}
	if err := os.WriteFile(cfg.ArtifactPath, []byte(`{"version":1,"encoder":"fixture","models":["strong"],"layers":[]}`), 0600); err != nil {
		t.Fatal(err)
	}
	if NewHierShrinkSelector(cfg, nil).loadError == nil {
		t.Fatal("accepted malformed profile")
	}
}

func TestHierShrinkEmbeddingAndCancellation(t *testing.T) {
	cfg := hierShrinkFixture(t)
	called := 0
	selector := NewHierShrinkSelector(cfg, func(query string) ([]float32, error) { called++; return []float32{0, 1}, nil })
	request := &SelectionContext{Query: "incident", QueryEmbedding: []float32{1, 0}, CandidateModels: []config.ModelRef{{Model: "strong"}, {Model: "cheap"}}}
	result, err := selector.Select(t.Context(), request)
	if err != nil || called != 1 || result.SelectedModel != "cheap" {
		t.Fatalf("embedding selection: %v %v", result, err)
	}
	ctx, cancel := context.WithCancel(t.Context())
	cancel()
	if _, err := selector.Select(ctx, request); err != context.Canceled || called != 1 {
		t.Fatalf("cancellation: %v", err)
	}
}

func BenchmarkHierShrink(b *testing.B) {
	selector := NewHierShrinkSelector(hierShrinkFixture(b), nil)
	request := &SelectionContext{QueryEmbedding: []float32{1, 0}, CandidateModels: []config.ModelRef{{Model: "strong"}, {Model: "cheap"}}}
	b.ResetTimer()
	for b.Loop() {
		if _, err := selector.Select(b.Context(), request); err != nil {
			b.Fatal(err)
		}
	}
}
