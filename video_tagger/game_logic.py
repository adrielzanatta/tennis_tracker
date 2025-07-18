def determine_winner(point_data: dict) -> str:
    """
    Lógica de negócio centralizada para determinar o vencedor de um ponto
    com base em sua lista de eventos.

    Args:
        point_data: Dicionário contendo os eventos do ponto. 
    Returns:
        O código do jogador vencedor ('A' ou 'B') ou None se não for possível determinar.
    """
    if not point_data or not point_data.get("events"):
        return None
        
    events = point_data["events"]
    # O sacador é definido pelo primeiro evento do ponto
    server = events[0]["event_code"]
    receiver = "B" if server == "A" else "A"
    
    num_shots = len(events)
    # O último golpe foi do sacador se o número de eventos for ímpar
    last_shot_by_server = (num_shots % 2 == 1)
    
    last_event_code = events[-1]["event_code"]

    if last_event_code == "W":  # Winner
        return server if last_shot_by_server else receiver
    elif last_event_code == "E":  # Error
        return receiver if last_shot_by_server else server
    
    return None