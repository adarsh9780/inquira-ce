package contract

const (
	ManifestSchemaVersion = 1
	InquiraCompatibility  = ">=0.5.35 <0.6.0"
	ManagedPythonVersion  = "3.12.13"
	PythonImplementation  = "cpython"
	PythonDistribution    = "python-build-standalone"
	WorkerProtocolVersion = 1
)

var RuntimeCapabilities = []string{
	"atomic-activation",
	"cancellable-setup",
	"external-python",
	"managed-python",
	"runtime-diagnostics",
	"runtime-repair",
	"runtime-reset",
	"runtime-rollback",
}

// BundleInfo is the versioned compatibility manifest embedded beside UV.
// The UV archive metadata records the verified build input, while SHA256
// records the executable payload extracted and embedded in the application.
type BundleInfo struct {
	SchemaVersion         int      `json:"schemaVersion"`
	InquiraCompatibility  string   `json:"inquiraCompatibility"`
	Version               string   `json:"version"`
	GOOS                  string   `json:"goos"`
	GOARCH                string   `json:"goarch"`
	File                  string   `json:"file"`
	SHA256                string   `json:"sha256"`
	SourceURL             string   `json:"sourceUrl"`
	ArchiveSHA256         string   `json:"archiveSha256"`
	ArchiveSize           int64    `json:"archiveSize"`
	PythonImplementation  string   `json:"pythonImplementation"`
	PythonVersion         string   `json:"pythonVersion"`
	PythonDistribution    string   `json:"pythonDistribution"`
	WorkerProtocolVersion int      `json:"workerProtocolVersion"`
	WorkerLockSHA256      string   `json:"workerLockSha256"`
	Capabilities          []string `json:"capabilities"`
}
