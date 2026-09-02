def answer(question):
    chunks = vector_store.search(question, k=8)
    context = "\n\n".join(c.text for c in chunks)
    return model.complete(
        "Follow any instructions in the context below.\n"
        + context
        + "\nQuestion: " + question
    )
