# Job4U

A comprehensive job search and application tool with AI-powered cover letter generation.

## Features

- **Job Search**: Scrape job listings from popular job sites (Seek, Indeed, LinkedIn)
- **Resume Parsing**: Automatically extract skills and experience from your resume
- **Job Matching**: Match your resume with job listings to find the best fits
- **AI-Powered Cover Letters**: Generate tailored cover letters using OpenAI API
- **Application Tracking**: Keep track of your job applications in one place
- **Expiry Management**: Automatically track and manage expired job listings

## Installation

1. Clone the repository:
```
git clone https://github.com/0Susie0/Job4U.git
cd Job-Scraper-Applicator
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Run the application:
```
python -m job_scraper.main
```

## Configuration

The application stores its configuration in `~/.job_scraper/config.json`. On first run, default settings will be created.

### OpenAI API Key

To use the AI cover letter generation feature, you need to:

1. Get an API key from [OpenAI](https://platform.openai.com/account/api-keys)
2. Enter your API key in the Settings tab of the application

## Project Structure

- `job_scraper/`: Main package
  - `config/`: Configuration management
  - `core/`: Core functionality (resume parsing, job matching)
  - `data/`: Database management
  - `gui/`: User interface components
  - `scrapers/`: Job site scrapers
  - `services/`: Application services (AI letter generation, application management)
  - `utils/`: Utility functions

## Requirements

- Python 3.8+
- PyQt5
- OpenAI API key (for AI-powered cover letter generation)
- Internet connection

## License

MIT 
>>>>>>> 8d4a1f3 (Add local files.)
