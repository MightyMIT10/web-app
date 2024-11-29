# AI Influencer App

A Flask-based web application that creates AI-generated videos using the Heygen API. Users can select avatars, create videos, and manage their video content through a user-friendly interface.

## Features

- Create AI-generated videos with custom avatars
- View and manage created videos
- Real-time video status updates
- Customizable video titles
- Modern, responsive user interface

## Prerequisites

- Python 3.8 or higher
- Heygen API key
- Flask and other dependencies (listed in requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-influencer-app.git
cd ai-influencer-app
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory and add your Heygen API key:
```
HEYGEN_API_KEY=your_api_key_here
```

5. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
ai_influencer_app/
├── app.py                    # Main Flask application
├── style.css                # CSS styles
├── default-thumbnail.svg    # Default video thumbnail
├── index.html              # Home page
├── template_avatars.html    # Avatars page template
├── template_submit.html     # Video creation page template
├── template_videos.html     # Video management page template
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore rules
├── LICENSE                 # MIT License
└── README.md               # Project documentation
```

## Environment Variables

- `HEYGEN_API_KEY`: Your Heygen API key (required)

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/improvement`)
3. Make your changes
4. Commit your changes (`git commit -am 'Add new feature'`)
5. Push to the branch (`git push origin feature/improvement`)
6. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
