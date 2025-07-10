# Calculate the result of the given codes for each tennis stroke recorded
def code_to_point(code: str) -> str:
    if len(code) % 2 == 0:
        match code[-1]:
            case "W":
                return "A" if code[0] == "B" else "B"
            case "E":
                return code[0]
    else:
        match code[-1]:
            case "W":
                return code[0]
            case "E":
                return "B" if code[0] == "A" else "A"


def calculate_games(codes: list) -> None:
    points_a = 0
    points_b = 0
    games_a = 0
    games_b = 0

    for i, code in enumerate(codes):
        point = code_to_point(code)
        if point == "A":
            points_a += 1
        else:
            points_b += 1

        if points_a >= 4 and points_a - points_b >= 2:
            games_a += 1
            points_a, points_b = 0, 0

        elif points_b >= 4 and points_b - points_a >= 2:
            games_b += 1
            points_a, points_b = 0, 0
        print(i + 1, code, point)
        print(f"A |{games_a}|{points_a}\nB |{games_b}|{points_b}\n----")
