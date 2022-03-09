import importlib

spec = importlib.util.spec_from_file_location("*", "can_we_talk.py")

oscc_check = importlib.util.module_from_spec(spec)

spec.loader.exec_module(oscc_check)
