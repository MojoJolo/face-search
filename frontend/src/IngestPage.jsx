import { useState } from 'react';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

const initialForm = {
  folder_path: '/data/photos',
  recursive: true,
  min_face_size: 80,
  det_threshold: 0.6,
  max_faces: 20,
};

function getPreviewUrl(imagePath) {
  return `${apiBaseUrl}/image-preview?path=${encodeURIComponent(imagePath)}`;
}

function PreviewImage({ imagePath, faces }) {
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
          {faces.map((face, index) => (
            <rect
              key={`${imagePath}-${index}`}
              className="face-box"
              x={face.bbox.x1}
              y={face.bbox.y1}
              width={Math.max(face.bbox.x2 - face.bbox.x1, 0)}
              height={Math.max(face.bbox.y2 - face.bbox.y1, 0)}
              rx="10"
              ry="10"
            >
              <title>{`det=${face.det_score.toFixed(3)}`}</title>
            </rect>
          ))}
        </svg>
      ) : null}
    </div>
  );
}

export default function IngestPage() {
  const [form, setForm] = useState(initialForm);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setResponse(null);

    try {
      const res = await fetch(`${apiBaseUrl}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          min_face_size: Number(form.min_face_size),
          det_threshold: Number(form.det_threshold),
          max_faces: Number(form.max_faces),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Ingest failed');
      }
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function updateField(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="section-tag">Folder Ingest</p>
          <h2>Index mounted photos</h2>
        </div>
        <p className="hint">Default Docker mount: `/data/photos`</p>
      </div>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          Folder path
          <input
            value={form.folder_path}
            onChange={(event) => updateField('folder_path', event.target.value)}
          />
        </label>
        <label>
          Min face size
          <input
            type="number"
            min="1"
            value={form.min_face_size}
            onChange={(event) => updateField('min_face_size', event.target.value)}
          />
        </label>
        <label>
          Detection threshold
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={form.det_threshold}
            onChange={(event) => updateField('det_threshold', event.target.value)}
          />
        </label>
        <label>
          Max faces per image
          <input
            type="number"
            min="1"
            value={form.max_faces}
            onChange={(event) => updateField('max_faces', event.target.value)}
          />
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={form.recursive}
            onChange={(event) => updateField('recursive', event.target.checked)}
          />
          Scan subfolders recursively
        </label>
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? 'Indexing...' : 'Start ingest'}
        </button>
      </form>

      {error ? <p className="error-banner">{error}</p> : null}

      {response ? (
        <div className="result-card">
          <h3>Run Summary</h3>
          <p>Images processed: {response.images_processed}</p>
          <p>Faces stored: {response.faces_stored}</p>
          <p>Preview images: {response.preview_images.length}</p>
          <p>Skipped files: {response.skipped_files.length}</p>
          {response.preview_images.length > 0 ? (
            <div className="results-grid">
              {response.preview_images.map((image) => (
                <article key={image.image_path} className="match-card">
                  <PreviewImage imagePath={image.image_path} faces={image.faces} />
                  <p className="match-path">{image.image_path}</p>
                  <p>Faces detected: {image.faces.length}</p>
                </article>
              ))}
            </div>
          ) : null}
          {response.skipped_files.length > 0 ? (
            <pre>{JSON.stringify(response.skipped_files, null, 2)}</pre>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
