from app.consoles.mock import MockAdapter
from app.consoles.sq import SQAdapter
from app.consoles.x32 import X32Adapter

ADAPTERS = {a.name: a for a in (MockAdapter, SQAdapter, X32Adapter)}
