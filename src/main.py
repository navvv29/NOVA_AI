import uuid

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage  # noqa: E402

from src.agent import graph  # noqa: E402


def new_thread_config() -> dict:
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def main() -> None:
    config = new_thread_config()
    print("N.O.V.A is online. Type 'exit' to quit, '/new' to reset memory.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nShutting down.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Shutting down.")
            break
        if user_input.lower() == "/new":
            config = new_thread_config()
            print("(started a fresh conversation)\n")
            continue

        result = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )
        reply = result["messages"][-1]
        print(f"Nova: {reply.content}\n")


if __name__ == "__main__":
    main()
