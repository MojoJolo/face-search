import { useCallback, useEffect, useRef, useState } from 'react';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';

const initialParams = {
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

function ProgressBar({ processed, total }) {
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0;
  return (
    <div className="progress-wrap">
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="progress-label">
        {processed} / {total} images ({pct}%)
      </span>
    </div>
  );
}

export default function IngestPage() {
  const [params, setParams] = useState(initialParams);
  const [files, setFiles] = useState([]);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/ingested-images`);
      if (!res.ok) return;
      const data = await res.json();
      setHistory(data.images);
      setHistoryTotal(data.total);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadHistory();
    return stopPolling;
  }, [loadHistory, stopPolling]);

  function startPolling(jobId) {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${apiBaseUrl}/ingest-status/${jobId}`);
        if (!res.ok) return;
        const data = await res.json();
        setJob(data);

        if (data.status === 'completed' || data.status === 'failed') {
          stopPolling();
          setLoading(false);
          if (data.status === 'completed') {
            setResponse(data);
            loadHistory();
          } else {
            setError(data.error || 'Ingest failed');
          }
        }
      } catch {
        // keep polling on transient network errors
      }
    }, 1000);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (files.length === 0) {
      setError('Please select at least one image.');
      return;
    }
    setLoading(true);
    setError('');
    setResponse(null);
    setJob(null);

    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    formData.append('min_face_size', String(params.min_face_size));
    formData.append('det_threshold', String(params.det_threshold));
    formData.append('max_faces', String(params.max_faces));

    try {
      const res = await fetch(`${apiBaseUrl}/ingest-upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Ingest failed');
      }
      startPolling(data.job_id);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  function updateParam(key, value) {
    setParams((current) => ({ ...current, [key]: value }));
  }

  function handleFileChange(event) {
    setFiles(Array.from(event.target.files));
  }

  function handleDrop(event) {
    event.preventDefault();
    const dropped = Array.from(event.dataTransfer.files).filter((f) =>
      f.type.startsWith('image/'),
    );
    setFiles(dropped);
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="section-tag">Photo Ingest</p>
          <h2>Upload photos to index</h2>
        </div>
        <p className="hint">
          {files.length > 0 ? `${files.length} file(s) selected` : 'Select images to upload'}
        </p>
      </div>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label
          className="file-upload-area"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <span className="file-upload-icon">&#8593;</span>
          {files.length === 0 ? (
            <>
              <span className="file-upload-primary">Click or drag &amp; drop images</span>
              <span className="file-upload-sub">JPG, PNG, WEBP, BMP supported</span>
            </>
          ) : (
            <>
              <span className="file-upload-primary">{files.length} image(s) selected</span>
              <span className="file-upload-sub">Click to change selection</span>
            </>
          )}
        </label>

        <label>
          Min face size
          <input
            type="number"
            min="1"
            value={params.min_face_size}
            onChange={(event) => updateParam('min_face_size', event.target.value)}
          />
        </label>
        <label>
          Detection threshold
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={params.det_threshold}
            onChange={(event) => updateParam('det_threshold', event.target.value)}
          />
        </label>
        <label>
          Max faces per image
          <input
            type="number"
            min="1"
            value={params.max_faces}
            onChange={(event) => updateParam('max_faces', event.target.value)}
          />
        </label>
        <button className="primary-button" type="submit" disabled={loading || files.length === 0}>
          {loading ? 'Indexing...' : 'Start ingest'}
        </button>
      </form>

      {loading && job ? (
        <div className="result-card">
          <h3>Processing...</h3>
          <ProgressBar processed={job.images_processed} total={job.images_total} />
          {job.current_file ? <p className="hint">Current: {job.current_file}</p> : null}
        </div>
      ) : null}

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

      {history.length > 0 ? (
        <div className="result-card">
          <h3>Indexed Images ({historyTotal})</h3>
          <div className="results-grid">
            {history.map((image) => (
              <article key={image.image_path} className="match-card">
                <PreviewImage imagePath={image.image_path} faces={image.faces} />
                <p className="match-path">{image.image_path}</p>
                <p>Faces: {image.faces.length}</p>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
