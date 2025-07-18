import cv2
import argparse
import os
import copy
from tqdm import tqdm

# Assuming these modules are in the same directory or accessible via PYTHONPATH
from game import TennisGame
from scoreboard import Scoreboard
from ui_handler import UIHandler
from game_logic import determine_winner
from csv_handler import CSVHandler


def create_highlights(video_path, csv_path, output_path, player_a, player_b, initial_server, buffer_sec=1.0):
    """
    Cuts a video based on point timestamps from a CSV and adds a scoreboard.
    This version reads the source video sequentially only once for performance.

    Args:
        video_path (str): Path to the original, unoptimized video file.
        csv_path (str): Path to the analysis CSV file.
        output_path (str): Path to save the generated highlights video.
        player_a (str): Name of Player A.
        player_b (str): Name of Player B.
        initial_server (str): The player who served first ('A' or 'B').
        buffer_sec (float): Seconds to add before and after each point.
    """
    # 1. --- SETUP ---
    print("Initializing and preparing clip segments...")

    csv_handler = CSVHandler(csv_path)
    all_points_data = csv_handler.load_csv()
    if not all_points_data:
        print("No points found in the CSV file. Exiting.")
        return

    # Sort points by their ID to ensure chronological order
    all_points_data.sort(key=lambda p: p['point_id'])

    # Initialize video capture
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video Info: {width}x{height} @ {fps:.2f} FPS, {total_frames} frames total.")

    # Initialize video writer
    fourcc = cv2.VideoWriter().fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        print(f"Error: Could not open video writer for {output_path}")
        cap.release()
        return

    # Initialize game logic and UI components
    game = TennisGame(player_a, player_b, initial_server=initial_server)
    scoreboard_presenter = Scoreboard()
    ui_handler = UIHandler(window_name="Video Cutter (Processing)")
    cv2.destroyWindow("Video Cutter (Processing)")

    buffer_frames = int(buffer_sec * fps)

    # 2. --- PREPARE CLIPS TO RENDER ---
    # Create a list of all segments (start_frame, end_frame, game_state) to be included.
    clips_to_render = []
    for point_data in all_points_data:
        # Store the game state *before* this point is played for correct scoreboard display
        game_state_for_point = copy.deepcopy(game)

        start_frame = point_data["events"][0]["event_frame"]
        end_frame = point_data["events"][-1]["event_frame"]

        clip_start_frame = max(0, start_frame - buffer_frames)
        clip_end_frame = min(total_frames - 1, end_frame + buffer_frames)

        clips_to_render.append((clip_start_frame, clip_end_frame, game_state_for_point))

        # Update the main game state for the next point
        winner = determine_winner(point_data)
        if winner:
            game.point_won_by(winner)
        else:
            print(f"Warning: Could not determine winner for point {point_data['point_id']}. Score may be incorrect going forward.")

    if not clips_to_render:
        print("No valid clips to render. Exiting.")
        cap.release()
        out.release()
        return

    # 3. --- SEQUENTIAL PROCESSING LOOP ---
    print(f"Processing {total_frames} frames from source video...")
    
    clip_iterator = iter(clips_to_render)
    current_clip = next(clip_iterator, None)

    try:
        with tqdm(total=total_frames, desc="Creating Highlights") as pbar:
            for frame_num in range(total_frames):
                ret, frame = cap.read()
                pbar.update(1)
                if not ret:
                    break # End of video

                if current_clip is None:
                    # No more clips to process, we can stop reading.
                    break
                
                clip_start, clip_end, game_state = current_clip

                # Check if the current frame is within the current clip's range
                if frame_num >= clip_start and frame_num <= clip_end:
                    score_data = scoreboard_presenter.get_score_data(game_state)
                    ui_handler.draw_scoreboard(frame, score_data)
                    out.write(frame)
                
                # If we've passed the end of the current clip, get the next one
                if frame_num >= clip_end:
                    current_clip = next(clip_iterator, None)
    finally:
        # 4. --- CLEANUP ---
        print("Finalizing video...")
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        print(f"\nHighlights video saved successfully to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Create a highlights video from a tennis match analysis.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("video_path", help="Path to the original (unoptimized) video file.")
    parser.add_argument("csv_path", help="Path to the analysis CSV file generated by the tagger.")
    parser.add_argument("output_path", help="Path to save the final highlights video (e.g., 'highlights/match1.mp4').")
    parser.add_argument("--player_a", default="Player A", help="Name of Player A.")
    parser.add_argument("--player_b", default="Player B", help="Name of Player B.")
    parser.add_argument("--server", choices=["A", "B"], default="A", help="Player who served first in the match.")
    parser.add_argument("--buffer", type=float, default=0.5, help="Buffer in seconds to add before and after each point. Default: 0.5")
    args = parser.parse_args()

    output_dir = os.path.dirname(args.output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    create_highlights(args.video_path, args.csv_path, args.output_path, args.player_a, args.player_b, args.server, args.buffer)

if __name__ == "__main__":
    main()