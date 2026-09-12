package extproc

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/vllm-project/semantic-router/src/semantic-router/pkg/config"
	"github.com/vllm-project/semantic-router/src/semantic-router/pkg/selection"
	"gopkg.in/yaml.v2"
)

func TestHierShrinkDecisionIntegration(t *testing.T) {
	selection.InitializeMetrics()
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		var body struct {
			Model string `json:"model"`
		}
		if err := json.NewDecoder(request.Body).Decode(&body); err != nil || body.Model != "fixture" {
			t.Errorf("embedding request: %v %v", body, err)
		}
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`{"data":[{"index":0,"embedding":[1,0]}]}`))
	}))
	defer server.Close()
	artifact, err := os.ReadFile("../selection/testdata/hiershrink.json")
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), "profile.json")
	if err := os.WriteFile(path, artifact, 0600); err != nil {
		t.Fatal(err)
	}
	router := &OpenAIRouter{Config: &config.RouterConfig{InlineModels: config.InlineModels{EmbeddingModels: config.EmbeddingModels{
		EmbeddingConfig: config.HNSWConfig{Backend: config.EmbeddingBackendOpenAICompatible, ModelType: config.EmbeddingModelTypeRemote, TargetDimension: 2},
		Endpoint:        config.EmbeddingEndpointConfig{BaseURL: server.URL + "/v1", Model: "fixture"},
	}}}}
	var algorithm config.AlgorithmConfig
	if err := yaml.Unmarshal([]byte("type: hiershrink\nhiershrink:\n  embedding_model: fixture\n  embedding_dimension: 2\n  cost_weight: 1\n"), &algorithm); err != nil {
		t.Fatal(err)
	}
	algorithm.HierShrink.ArtifactPath = path
	request := &selection.SelectionContext{Query: "incident", QueryEmbedding: []float32{0, 1}, CandidateModels: []config.ModelRef{{Model: "strong"}, {Model: "cheap"}}}
	selected, method, err := router.selectModelFromCandidates(request, &algorithm, &RequestContext{})
	if err != nil || method != "hiershrink" || selected.Model != "cheap" {
		t.Fatalf("selection: %v %s %v", selected, method, err)
	}
	first := router.hierShrinkSelector(algorithm.HierShrink)
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	if first != router.hierShrinkSelector(algorithm.HierShrink) {
		t.Fatal("artifact is not cached")
	}
	selected, _, err = router.selectModelFromCandidates(request, &algorithm, &RequestContext{})
	if err != nil || selected.Model != "cheap" {
		t.Fatalf("cached selection: %v %v", selected, err)
	}
	algorithm.HierShrink.CostWeight = 0
	requestContext := &RequestContext{}
	selected, _, err = router.selectModelFromCandidates(request, &algorithm, requestContext)
	if err != nil || selected.Model != "strong" || requestContext.VSRSelectionReasoning != selectionFallbackError {
		t.Fatalf("load failure fallback: %v %v %v", selected, err, requestContext.VSRSelectionReasoning)
	}
}
