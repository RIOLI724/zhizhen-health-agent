"""测试隔离：临时向量库 + 强制 Mock 模型，保证测试不依赖外部服务。

真实 Key 在 backend/.env 里（生产用），但测试必须零 Key 走规则与模板。
"""

import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="zhizhen-test-")
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_API_KEY"] = ""
os.environ["EMBEDDING_PROVIDER"] = "mock"
