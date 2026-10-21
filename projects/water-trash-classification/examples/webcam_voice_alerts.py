# Historical webcam prototype retained from the course project.
# Requires a matching keras_model.h5 and labels.txt in the working directory.
# Those artifacts are not bundled because the original label mapping is missing.
# This is whole-frame classification; the rectangle does not localize an object.
# The recycling-status strings are demonstration rules, not disposal guidance.
import cv2
import numpy as np
from keras.models import load_model
import pyttsx3  # For text-to-speech
import time  # For handling delay

# Disable scientific notation for clarity
np.set_printoptions(suppress=True)

# Load the model
model = load_model("keras_model.h5", compile=False)

# Load the labels
class_names = open("labels.txt", "r").readlines()

# CAMERA can be 0 or 1 based on the default camera of your computer
camera = cv2.VideoCapture(0)

# Prediction control flag
prediction_active = False

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Timer for counting predictions in certain periods
prediction_count = 0
start_time = cv2.getTickCount()  # Time tracking in ticks

# Timestamp for voice alert delay
last_alert_time = 0  # Tracks the time of the last voice alert

# Print instructions
print("Press 's' to start prediction, 'q' to stop prediction, and 'Esc' to exit.")

while True:
    # Grab the webcam's image.
    ret, image = camera.read()

    # Check if prediction is active
    if prediction_active:
        # Create a resized copy for prediction without altering the original image
        resized_image = cv2.resize(image, (224, 224), interpolation=cv2.INTER_AREA)

        # Make the image a numpy array and reshape it to the model's input shape.
        input_image = np.asarray(resized_image, dtype=np.float32).reshape(1, 224, 224, 3)

        # Normalize the image array
        input_image = (input_image / 127.5) - 1

        # Predict using the model
        prediction = model.predict(input_image, verbose=0)
        index = np.argmax(prediction)
        class_name = class_names[index].strip()  # Remove any extra whitespace
        confidence_score = prediction[0][index]

        # Draw bounding box (for simplicity, we'll draw a box around the entire image)
        height, width, _ = image.shape
        cv2.rectangle(image, (0, 0), (width, height), (0, 255, 0), 2)

        # If confidence is higher than 70%, display prediction
        if confidence_score > 0.6:
            # Determine recycling status
            if class_name == "0 blank":
                recycling_status = "No material detected"
            elif class_name == "4 plastic bag":
                recycling_status = "Non-recycled"
            else:
                recycling_status = "Recycle"
            
            # Prepare text for display
            prediction_text = f"Class: {class_name.split(' ', 1)[-1]}"
            confidence_text = f"Confidence: {confidence_score * 100:.2f}%"
            status_text = f"Status: {recycling_status}"

            # Overlay text on the original image
            cv2.putText(image, prediction_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(image, confidence_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(image, status_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

            # Count predictions within a 10-second window
            if (cv2.getTickCount() - start_time) / cv2.getTickFrequency() >= 10:
                print(f"Predictions in last 10 seconds: {prediction_count}")
                prediction_count = 0
                start_time = cv2.getTickCount()  # Reset timer

            # Increment prediction count
            prediction_count += 1

            # If confidence is greater than 85%, trigger voice alert and stop prediction
            current_time = time.time()  # Current timestamp
            if confidence_score > 0.85 and class_name != "0 blank" and (current_time - last_alert_time) >= 3:
                class_name = class_names[index].strip().split(' ', 1)[-1]  # Remove numeric part
                engine.say(f"High confidence detected: {class_name} with {confidence_score * 100:.0f}% confidence.")
                engine.runAndWait()
                last_alert_time = current_time  # Update the last alert time
                print(f"Prediction stopped for {class_name} with confidence: {confidence_score * 100:.2f}%")
                prediction_active = False

        else:
            # If confidence is less than or equal to 70%, show no prediction
            cv2.putText(image, "Confidence too low", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

    # Show the original image with overlayed text
    cv2.imshow("Webcam Image", image)

    # Listen to the keyboard for presses.
    keyboard_input = cv2.waitKey(1)

    # 27 is the ASCII for the ESC key on your keyboard.
    if keyboard_input == 27:  # ESC to exit
        break
    elif keyboard_input == ord('s'):  # 'S' to start prediction
        prediction_active = True
    elif keyboard_input == ord('q'):  # 'Q' to stop prediction
        prediction_active = False

camera.release()
cv2.destroyAllWindows()
