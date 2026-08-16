def test_imports():
 from app.audit import log_interaction,verify_chain
 assert callable(log_interaction) and callable(verify_chain)
