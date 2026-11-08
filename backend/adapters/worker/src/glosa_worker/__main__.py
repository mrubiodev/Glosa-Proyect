"""El worker necesita la composición del sistema, que vive en `glosa_app`."""
import sys

print("glosa: el worker se ejecuta con `python -m glosa_app worker`.", file=sys.stderr)
sys.exit(2)
