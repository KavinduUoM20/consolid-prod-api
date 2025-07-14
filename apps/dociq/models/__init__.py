# Import all models so SQLAlchemy can discover them
from .template import Template
from .document import Document
from .extraction import Extraction
from .target_mapping import TargetMapping

__all__ = ["Template", "Document", "Extraction", "TargetMapping"] 