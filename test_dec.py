from app import storage

# Retrieve decrypted
retrieved = storage.get_record("patient123")
print("Retrieved record:", retrieved)