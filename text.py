import importlib
genai = importlib.import_module("google.genai")
print("genai version:", getattr(genai, "__version__", "unknown"))
print("module path  :", genai.__file__)
