from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, computed_field


class DocumentType(str, Enum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"


class DocumentMetadata(BaseModel):
    source: str = Field(..., description="Original document source path")
    type: DocumentType = Field(..., description="Document type")
    file_path: str = Field(..., description="Full file path")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ProcessedContent(BaseModel):
    id: str = Field(..., pattern=r"^doc_[A-Za-z0-9_]+$", description="Document identifier")
    raw_text: str = Field(..., min_length=1, description="Extracted text content")
    metadata: DocumentMetadata
    processing_timestamp: datetime
    language: str = Field(default="en", description="Detected language")
    sections: List[Dict[str, str]] = Field(default_factory=list)
    extraction_errors: List[str] = Field(default_factory=list)

    @field_validator('raw_text', mode='before')
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip() if v else ""

    @computed_field
    @property
    def word_count(self) -> int:
        """Calculate word count from raw text."""
        return len(self.raw_text.split()) if self.raw_text else 0


class ContentBatch(BaseModel):
    batch_id: str
    job_id: str
    documents: List[ProcessedContent]
    created_at: datetime

    @computed_field
    @property
    def total_documents(self) -> int:
        """Calculate total number of documents."""
        return len(self.documents)