import sys, pkgutil
print('executable:', sys.executable)
print('uvicorn:', pkgutil.find_loader('uvicorn') is not None)
print('streamlit:', pkgutil.find_loader('streamlit') is not None)
