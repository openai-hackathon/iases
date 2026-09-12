package selection

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"os"

	"github.com/vllm-project/semantic-router/src/semantic-router/pkg/config"
)

const MethodHierShrink SelectionMethod = "hiershrink"

type hierShrinkLayer struct {
	Weights [][]float64 `json:"weights"`
	Bias    []float64   `json:"bias"`
}

type hierShrinkArtifact struct {
	Version int               `json:"version"`
	Encoder string            `json:"encoder"`
	Models  []string          `json:"models"`
	Costs   []float64         `json:"costs"`
	Layers  []hierShrinkLayer `json:"layers"`
	Profile [][]float64       `json:"profile"`
	Offset  []float64         `json:"offset"`
	Table   [][]float64       `json:"table"`
	Centers [][]float64       `json:"centers"`
}

type HierShrinkSelector struct {
	artifact  hierShrinkArtifact
	config    config.HierShrinkSelectionConfig
	embed     func(string) ([]float32, error)
	loadError error
}

func NewHierShrinkSelector(cfg config.HierShrinkSelectionConfig, embed func(string) ([]float32, error)) *HierShrinkSelector {
	selector := &HierShrinkSelector{config: cfg, embed: embed}
	selector.loadError = selector.load()
	return selector
}

func (selector *HierShrinkSelector) load() error {
	if selector.config.ArtifactPath == "" || selector.config.EmbeddingModel == "" || selector.config.EmbeddingDimension < 1 || !finiteHierShrink(selector.config.CostWeight) || selector.config.CostWeight < 0 {
		return fmt.Errorf("invalid HierShrink configuration")
	}
	file, err := os.Open(selector.config.ArtifactPath)
	if err != nil {
		return err
	}
	defer file.Close()
	decoder := json.NewDecoder(io.LimitReader(file, 64<<20))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&selector.artifact); err != nil {
		return err
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		return fmt.Errorf("unexpected trailing HierShrink artifact data")
	}
	artifact := &selector.artifact
	count := len(artifact.Models)
	if artifact.Version != 1 || artifact.Encoder != selector.config.EmbeddingModel || count == 0 || len(artifact.Layers) != 3 {
		return fmt.Errorf("incompatible HierShrink artifact")
	}
	seen := make(map[string]bool, count)
	for _, model := range artifact.Models {
		if model == "" || seen[model] {
			return fmt.Errorf("invalid HierShrink model IDs")
		}
		seen[model] = true
	}
	dimension := selector.config.EmbeddingDimension
	for _, layer := range artifact.Layers {
		if len(layer.Bias) == 0 || !validHierShrinkVector(layer.Bias, len(layer.Weights)) || !validHierShrinkMatrix(layer.Weights, len(layer.Bias), dimension) {
			return fmt.Errorf("invalid HierShrink layer")
		}
		dimension = len(layer.Bias)
	}
	if !validHierShrinkMatrix(artifact.Profile, dimension, count) || !validHierShrinkVector(artifact.Offset, count) || !validHierShrinkVector(artifact.Costs, count) || len(artifact.Centers) == 0 || !validHierShrinkMatrix(artifact.Centers, len(artifact.Centers), selector.config.EmbeddingDimension) || !validHierShrinkMatrix(artifact.Table, len(artifact.Centers), count) {
		return fmt.Errorf("invalid HierShrink profile dimensions or values")
	}
	for _, cost := range artifact.Costs {
		if cost < 0 {
			return fmt.Errorf("negative HierShrink cost")
		}
	}
	return nil
}

func finiteHierShrink(value float64) bool { return !math.IsNaN(value) && !math.IsInf(value, 0) }

func validHierShrinkVector(values []float64, size int) bool {
	if len(values) != size {
		return false
	}
	for _, value := range values {
		if !finiteHierShrink(value) {
			return false
		}
	}
	return true
}

func validHierShrinkMatrix(rows [][]float64, count, width int) bool {
	if len(rows) != count {
		return false
	}
	for _, row := range rows {
		if !validHierShrinkVector(row, width) {
			return false
		}
	}
	return true
}

func (selector *HierShrinkSelector) Select(ctx context.Context, request *SelectionContext) (*SelectionResult, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if err := ValidateSelectionContext(request); err != nil {
		return nil, err
	}
	if selector.loadError != nil {
		return nil, fmt.Errorf("load HierShrink: %w", selector.loadError)
	}
	embedding := request.QueryEmbedding
	if selector.embed != nil {
		var err error
		embedding, err = selector.embed(request.Query)
		if err != nil {
			return nil, err
		}
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if len(embedding) != selector.config.EmbeddingDimension {
		return nil, fmt.Errorf("HierShrink embedding dimension mismatch")
	}
	query := make([]float64, len(embedding))
	var norm float64
	for index, value := range embedding {
		query[index] = float64(value)
		norm += query[index] * query[index]
	}
	norm = math.Sqrt(norm)
	if !finiteHierShrink(norm) || math.Abs(norm-1) > 1e-3 {
		return nil, fmt.Errorf("HierShrink requires a near-unit embedding from %s", selector.config.EmbeddingModel)
	}
	values := query
	for layerIndex, layer := range selector.artifact.Layers {
		next := append([]float64(nil), layer.Bias...)
		for row, weights := range layer.Weights {
			for column, weight := range weights {
				next[row] += weight * values[column]
			}
			if layerIndex < 2 {
				next[row] = math.Max(0, next[row])
			}
		}
		values = next
	}
	maximum := math.Inf(-1)
	for _, value := range values {
		maximum = math.Max(maximum, value)
	}
	var total float64
	for index, value := range values {
		values[index] = math.Exp(value - maximum)
		total += values[index]
	}
	cell, similarity := 0, math.Inf(-1)
	for index, center := range selector.artifact.Centers {
		var score float64
		for column, value := range center {
			score += value * (query[column] / norm)
		}
		if score > similarity {
			cell, similarity = index, score
		}
	}
	result := &SelectionResult{Method: MethodHierShrink, Tier: TierExperimental, AllScores: make(map[string]float64), Score: math.Inf(-1), Reasoning: "Predicted quality minus weighted artifact cost; not calibrated confidence"}
	for _, candidate := range request.CandidateModels {
		column := -1
		for index, model := range selector.artifact.Models {
			if model == candidate.Model {
				column = index
				break
			}
		}
		if column < 0 {
			return nil, fmt.Errorf("HierShrink candidate %q has no profile", candidate.Model)
		}
		quality := selector.artifact.Offset[column] + selector.artifact.Table[cell][column]
		for index, probability := range values {
			quality += probability / total * selector.artifact.Profile[index][column]
		}
		if !finiteHierShrink(quality) {
			return nil, fmt.Errorf("nonfinite HierShrink prediction")
		}
		score := math.Max(0, math.Min(1, quality)) - selector.config.CostWeight*selector.artifact.Costs[column]
		if !finiteHierShrink(score) {
			return nil, fmt.Errorf("nonfinite HierShrink utility")
		}
		result.AllScores[candidate.Model] = score
		if score > result.Score {
			result.SelectedModel, result.LoRAName, result.Score = candidate.Model, candidate.LoRAName, score
		}
	}
	return result, nil
}

func (selector *HierShrinkSelector) Method() SelectionMethod { return MethodHierShrink }
func (selector *HierShrinkSelector) Tier() AlgorithmTier     { return TierExperimental }
func (selector *HierShrinkSelector) ExternalDependencies() []Dependency {
	return []Dependency{{Name: selector.config.ArtifactPath, Type: DependencyPretrainedModel, Required: true}, {Name: selector.config.EmbeddingModel, Type: DependencyEmbeddingFunc, Required: true}}
}
func (selector *HierShrinkSelector) UpdateFeedback(context.Context, *Feedback) error {
	return fmt.Errorf("HierShrink feedback requires an offline artifact rebuild")
}
