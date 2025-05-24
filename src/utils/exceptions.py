class DocumentProcessingError(Exception):
    """Raised when document cannot be parsed."""
    
    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        self.message = message
        super().__init__(f"Document processing failed for {file_path}: {message}")


class ScoringError(Exception):
    """Raised when scoring fails."""
    
    def __init__(self, document_id: str, dimension: str, message: str):
        self.document_id = document_id
        self.dimension = dimension
        self.message = message
        super().__init__(f"Scoring failed for {document_id} in dimension {dimension}: {message}")


class WorkflowError(Exception):
    """Raised for workflow-level failures."""
    
    def __init__(self, job_id: str, node_name: str, message: str):
        self.job_id = job_id
        self.node_name = node_name
        self.message = message
        super().__init__(f"Workflow error in {node_name} for job {job_id}: {message}")


class ConfigurationError(Exception):
    """Raised for invalid configuration."""
    
    def __init__(self, setting_name: str, message: str):
        self.setting_name = setting_name
        self.message = message
        super().__init__(f"Configuration error for {setting_name}: {message}")


class BatchProcessingError(Exception):
    """Raised when batch fails."""
    
    def __init__(self, failed_count: int, total_count: int, message: str):
        self.failed_count = failed_count
        self.total_count = total_count
        self.message = message
        super().__init__(f"Batch processing failed: {failed_count}/{total_count} documents failed - {message}")