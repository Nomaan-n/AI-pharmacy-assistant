from dataclasses import dataclass
import re
import httpx
from .config import get_settings
from .india_drugs import DailyMedRetriever as _UnusedDailyMedRetriever if False else None
