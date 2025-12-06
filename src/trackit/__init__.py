# Import main lazily to avoid circular dependencies
def __getattr__(name):
    if name == "main":
        from trackit.cli.main import main
        return main
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
