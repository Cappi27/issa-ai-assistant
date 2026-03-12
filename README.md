# Issa AI Visa Assistant

## 1. Overview
Issa is an intelligent, conversational AI travel assistant designed to help users navigate complex travel plans—specifically focusing on securing and understanding the Destination Thailand Visa (DTV) and similar long-term programs. 

By leveraging cutting-edge large language models, Issa acts as a personal visa consultant: understanding user situations, providing tailored guidance, formatting structured itineraries, and finally allowing users to quickly schedule 1-on-1 consultations directly into Google Calendar seamlessly from the chat interface.

## 2. Key Features
- **Conversational Visa Consulting:** Interacts naturally with users to evaluate their eligibility and clarify the complexities of Thai Visas.
- **Dynamic Meeting Scheduling:** The AI agent autonomously extracts requested consultation times and dates from the natural language context.
- **Premium Interface:** A modern, beautiful chat UI built with rich visuals, typing animations, and highly readable markdown-rendered AI responses.
- **In-Chat Calendar Integration:** When a meeting time is agreed upon, a beautiful "Save the Date" card is spawned inside the chat interface featuring the date, time, meeting type (e.g. Onsite), and Visa Type. 
- **Google Calendar Gateway:** Users can click "Save the Date" to be instantly redirected to a pre-filled Google Calendar event template.
- **Admin Appointment Tracking:** Every generated consultation slot is systematically tracked in an internal `appointments.json` file for administrative review and team tracking. 

## 3. Tech Stack
- **Backend:** Python 3, Flask
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **AI Integration:** OpenAI API (`gpt-4o-mini`)
- **Data Storage:** Local JSON (`appointments.json`)

## 4. Project Architecture
The architecture follows a classic Client-Server model optimized for real-time AI inference:
1. **Client (Browser):** The user types a message in the chat interface. The Javascript client captures the entire conversational sequence and sends it to the Flask backend to maintain rolling context.
2. **Server (Flask):** The application validates the sequence and injects a robust System Prompt, guiding the AI on its personality, markdown structuring constraints, and how to format scheduling slots. It then calls the OpenAI API.
3. **AI Inference:** The model generates the response, identifying if a consultation slot was successfully triggered. 
4. **Parsing & Rendering:** The client parses the AI's markdown response. If a scheduling block is detected, it natively extracts the Date, Time, Meeting Type, and Visa Type, decoupling it from the text bubble, and animating a "Save the Date" card.
5. **Calendar Routing:** Clicking the card pings the `/book-appointment` route, which logs the entry securely to `appointments.json` and responds with a 302 Redirect to Google Calendar with all event parameters natively populated.

## 5. Project Structure
```text
issa-ai-assistant/
├── server.py              # Main Flask backend application and routing logic
├── appointments.json      # System-managed database for internal appointment tracking
├── .env                   # Environment variable configuration (Ignored in Git)
├── templates/
│   ├── chat.html          # Chatbot interface & client-side logic
│   └── dashboard.html     # Administrative UI (WIP)
└── README.md              # Project documentation
```

## 6. Installation
Ensure you have Python 3.9+ installed natively on your machine.

1. Clone the repository:
```bash
git clone https://github.com/your-username/issa-ai-assistant.git
cd issa-ai-assistant
```

2. Create a virtual environment (optional but recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required Python dependencies:
```bash
pip install flask openai python-dotenv
```

## 7. Environment Variables Setup
You must configure your OpenAI access to allow Issa to function. 
Create a file named `.env` in the root directory:
```bash
touch .env
```
Inside `.env`, define your secret API key:
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
PORT=5000
```

## 8. Running the Project
Once installed and configured, launch the Flask server:
```bash
python3 server.py
```
Open your web browser and navigate to: [http://localhost:5000/chat](http://localhost:5000/chat)

## 9. API Endpoints
- `GET /`: Health check route verifying the app is running.
- `GET /chat`: Renders the main chat application UI.
- `POST /generate-reply`: Accepts `{ clientSequence: str, chatHistory: list }`. Queries OpenAI and returns the AI's markdown-formatted string.
- `GET /book-appointment`: Accepts URL query parameters `start`, `end`, `type`, and `visa_type`. Logs the event to `appointments.json` and issues a 302 redirect to the Google Calendar `TEMPLATE` action URL.

## 10. Calendar Integration Explanation
The Google Calendar integration operates without the overhead of OAuth. By carefully formatting the event details into Google's `calendar.google.com/calendar/render?action=TEMPLATE` URL endpoint, users are brought directly to their own familiar calendar app with the Title, Times, and details correctly pre-populated, leaving the user in full control of their own schedule. 

## 11. Appointment Tracking System
To provide the administration team with visibility into scheduled events, the backend maintains a lightweight local database file: `appointments.json`. 
When a user clicks "Save the Date", the `/book-appointment` route intercepts the request momentarily, appending a new record to the JSON array containing the Date, Time, Location, Visa Type, and an explicit `booked_at` UTC timestamp. This ensures the team has a permanent ledger of all prospective client consultations generated by the AI.

## 12. Future Improvements
- **Database Migration:** Transition from `appointments.json` to a robust relational database like PostgreSQL or SQLite.
- **Admin Dashboard Integration:** Build out `/dashboard.html` to consume the appointments data and provide visualization/analytics for the consulting team.
- **OAuth Google Calendar:** Integrate formal Google Calendar API OAuth to natively inject events onto the company's master calendar in real-time.
- **Document RAG:** Implement Retrieval-Augmented Generation (RAG) to allow the AI to actively read from official Thai Embassy PDFs to ensure changing laws are correctly cited. 

## 13. License
This project is licensed under the MIT License - see the LICENSE file for details.
