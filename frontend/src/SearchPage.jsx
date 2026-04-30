import { useState } from 'react';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

function getPreviewUrl(imagePath) {
  return `${apiBaseUrl}/image-preview?path=${encodeURIComponent(imagePath)}`;
}

function PreviewImage({ imagePath, bbox }) {
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  return (
    <div className="preview-media">
      <img
        src={getPreviewUrl(imagePath)}
        alt={imagePath}
        onLoad={(event) =>
          setDimensions({
            width: event.currentTarget.naturalWidth,
            height: event.currentTarget.naturalHeight,
          })
        }
      />
      {dimensions.width > 0 && dimensions.height > 0 ? (
        <svg
          className="face-overlay-layer"
          viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <rect
            className="face-box"
            x={bbox.x1}
            y={bbox.y1}
            width={Math.max(bbox.x2 - bbox.x1, 0)}
            height={Math.max(bbox.y2 - bbox.y1, 0)}
            rx="10"
            ry="10"
          />
        </svg>
      ) : null}
    </div>
  );
}

export default function SearchPage() {
  const [file, setFile] = useState(null);
  const [topK, setTopK] = useState(10);
  const [threshold, setThreshold] = useState(0.2);
  const [results, setResults] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSearch(event) {
    event.preventDefault();
    if (!file) {
      setError('Choose a selfie image first');
      return;
    }

    setLoading(true);
    setError('');
    setResults([]);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('top_k', String(topK));
    formData.append('threshold', String(threshold));

    try {
      const res = await fetch(`${apiBaseUrl}/search`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Search failed');
      }
      setResults(data.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="section-tag">Selfie Search</p>
          <h2>Find nearest face matches</h2>
        </div>
        <p className="hint">Upload exactly one face in the query image.</p>
      </div>

      <form className="form-grid" onSubmit={handleSearch}>
        <label>
          Selfie image
          <input type="file" accept="image/*" onChange={(event) => setFile(event.target.files?.[0] || null)} />
        </label>
        <label>
          Top K
          <input type="number" min="1" value={topK} onChange={(event) => setTopK(event.target.value)} />
        </label>
        <label>
          Similarity threshold
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={threshold}
            onChange={(event) => setThreshold(event.target.value)}
          />
        </label>
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error ? <p className="error-banner">{error}</p> : null}

      <div className="results-grid">
        {results.map((result) => (
          <article key={`${result.image_path}-${result.distance}`} className="match-card">
            <PreviewImage imagePath={result.image_path} bbox={result.bbox} />
            <p className="match-path">{result.image_path}</p>
            <p>Similarity: {result.similarity.toFixed(4)}</p>
            <p>Distance: {result.distance.toFixed(4)}</p>
            <p>
              BBox: [{result.bbox.x1}, {result.bbox.y1}, {result.bbox.x2}, {result.bbox.y2}]
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
