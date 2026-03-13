import argparse
from typing import List

from app.router import classify_intent, route_and_respond


TEST_MESSAGES: List[str] = [
    "how do i sort a list of objects in python?",
    "explain this sql query for me",
    "This paragraph sounds awkward, can you help me fix it?",
    "I'm preparing for a job interview, any tips?",
    "what's the average of these numbers: 12, 45, 23, 67, 34",
    "Help me make this better.",
    "I need to write a function that takes a user id and returns their profile, but also i need help with my resume.",
    "hey",
    "Can you write me a poem about clouds?",
    "Rewrite this sentence to be more professional.",
    "I'm not sure what to do with my career.",
    "what is a pivot table",
    "fxi thsi bug pls: for i in range(10) print(i)",
    "How do I structure a cover letter?",
    "My boss says my writing is too verbose.",
]


def run_batch_tests() -> None:
    print("Running batch tests with sample messages...\n")
    for idx, msg in enumerate(TEST_MESSAGES, start=1):
        print(f"[{idx}] User: {msg}")
        intent_obj = classify_intent(msg)
        print(f"    Classified intent: {intent_obj}")
        response = route_and_respond(msg, intent_obj)
        print("    Response:")
        print("    " + "\n    ".join(response.splitlines()))
        print("-" * 60)


def run_interactive() -> None:
    print("LLM Prompt Router CLI")
    print("Type your message and press Enter. Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye.")
            break

        intent_obj = classify_intent(user_input)
        print(f"[debug] intent: {intent_obj}")
        response = route_and_respond(user_input, intent_obj)
        print(f"Router: {response}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-powered prompt router")
    parser.add_argument(
        "--batch-test",
        action="store_true",
        help="Run a batch of predefined test messages and exit.",
    )
    args = parser.parse_args()

    if args.batch_test:
        run_batch_tests()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
