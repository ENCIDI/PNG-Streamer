from app.modules import logging_manager as logm, ui_manager as wm


logm.init_logging()
logm.get_logger(__name__).info("Application start")
wm.start_program()
