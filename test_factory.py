from topic_generation import (
    get_next_topic,
    increase_count
)

topics = get_next_topic(10)

for topic in topics:

    topic_code = topic[0]

    print(
        f"Yaratilmoqda: {topic_code}"
    )

    # keyin AI generator keladi

    increase_count(topic_code)

    print(
        f"Tugadi: {topic_code}"
    )
