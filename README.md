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

### Prerequisites

- Python 3.8 or higher
- Chrome browser installed (for web scraping)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/0Susie0/Job4U.git
   cd Job4U
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python run_gui.py
   ```

## Configuration

The application stores its configuration in `~/.job_scraper/config.json`. On first run, default settings will be created.

### Chrome WebDriver

The application uses Selenium with Chrome WebDriver for scraping job listings. You have two options for Chrome WebDriver:

1. **Automatic (Recommended)**: The application uses `webdriver_manager` to automatically download and manage the appropriate Chrome WebDriver version for your system. This option is enabled by default.

2. **Manual**: You can specify a path to your own Chrome WebDriver executable in the settings:
   - In the GUI: Go to Settings tab → Web Browser Settings → Chrome Driver Path
   - In the configuration file: Set the `chrome_driver_path` in your configuration file located at `~/.job_scraper/config.json`

### Browser Settings

You can configure the following browser settings:

- **Headless Mode**: Run the browser without a visible window (enabled by default)
- **Timeout**: Set the timeout for browser operations (default: 30 seconds)

### OpenAI API Key

To use the AI cover letter generation feature, you need to:

1. Get an API key from [OpenAI](https://platform.openai.com/account/api-keys)
2. Enter your API key in the Settings tab of the application

## Usage

1. **Set Up Your Profile**:
   - Enter your personal information in the Settings tab
   - Configure your resume path and job search preferences

2. **Search for Jobs**:
   - Enter keywords and location in the Search tab
   - Click "Search" to find matching jobs

3. **Review Jobs**:
   - View job details and match scores
   - Sort and filter jobs based on your preferences

4. **Generate Cover Letters**:
   - Select a job and generate a customized cover letter
   - Edit and save the cover letter as needed

5. **Apply to Jobs**:
   - Track your applications in the Applications tab

## Project Structure

- `job_scraper/`: Main package
  - `config/`: Configuration management
  - `core/`: Core functionality (resume parsing, job matching)
  - `data/`: Database management
  - `gui/`: User interface components
  - `scrapers/`: Job site scrapers
  - `services/`: Application services (AI letter generation, application management)
  - `utils/`: Utility functions

## Troubleshooting

### Chrome WebDriver Issues

If you encounter issues with Chrome WebDriver:

1. **Update Chrome**: Make sure your Chrome browser is up to date
2. **Manual WebDriver**: Try using a manually downloaded WebDriver version that matches your Chrome version
3. **WebDriver Path**: Ensure the path to your WebDriver is correct if using manual configuration
4. **Permissions**: Make sure the WebDriver executable has proper permissions

### Other Common Issues

- **Scraping Errors**: Some websites may block automated scraping; try using different job sites
- **API Limits**: Be aware of rate limits when making multiple searches

## Requirements

- Python 3.8+
- PyQt5
- OpenAI API key (for AI-powered cover letter generation)
- Internet connection

## License

This project is licensed under the MIT License - see the LICENSE file for details. 

