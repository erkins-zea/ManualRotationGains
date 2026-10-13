using UnityEngine;
using UnityEngine.Rendering;

// Only affects rendering while this scene is running; never moves the XR rig.
[DefaultExecutionOrder(-10000)]
public sealed class TerrainVRRendering : MonoBehaviour
{
    [SerializeField] private RenderPipelineAsset pipeline;
    [SerializeField, Range(0.1f, 2f)] private float terrainLodBias = 0.5f;
    private RenderPipelineAsset previousPipeline;
    private float previousLodBias;
    private bool applied;

    private void OnEnable()
    {
        if (pipeline == null) return;
        previousPipeline = QualitySettings.renderPipeline;
        previousLodBias = QualitySettings.lodBias;
        QualitySettings.renderPipeline = pipeline;
        QualitySettings.lodBias = terrainLodBias;
        applied = true;
    }

    private void OnDisable()
    {
        if (!applied) return;
        if (QualitySettings.renderPipeline == pipeline)
            QualitySettings.renderPipeline = previousPipeline;
        if (Mathf.Approximately(QualitySettings.lodBias, terrainLodBias))
            QualitySettings.lodBias = previousLodBias;
        applied = false;
    }
}
