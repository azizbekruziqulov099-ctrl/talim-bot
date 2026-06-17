

def build_lesson_steps(lesson):

    return [
        lesson["intro"],
        lesson["part_1"],
        lesson["part_2"],
        lesson["part_3"],
        lesson["part_4"],
        lesson["summary"]
    ]


def get_step_content(steps, step):

    if step < 0:
        return None

    if step >= len(steps):
        return None

    return steps[step]

def lesson_to_dict(row):

    return {
        "topic_code": row[0],
        "intro": row[1],
        "part_1": row[2],
        "part_2": row[3],
        "part_3": row[4],
        "part_4": row[5],
        "simple_1": row[6],
        "simple_2": row[7],
        "example_1": row[8],
        "example_2": row[9],
        "exercise_1": row[10],
        "exercise_2": row[11],
        "summary": row[12]
    }
