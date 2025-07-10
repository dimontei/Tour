import requests
from bs4 import BeautifulSoup
import csv
import sys

def scrape_tour_de_france_stage(url):
    """
    Scrape Tour de France stage results from ProCyclingStats
    
    Args:
        url (str): URL of the stage results page
    
    Returns:
        list: List of dictionaries containing the stage results
    """
    
    # Headers to mimic a real browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("Fetching page...")
        # Send GET request
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        print(f"Page fetched successfully. Status code: {response.status_code}")
        
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        print("HTML parsed successfully")
        
        # Debug: Print page title
        title = soup.find('title')
        if title:
            print(f"Page title: {title.text.strip()}")
        
        # Debug: Look for different possible table classes/structures
        print("\nLooking for results table...")
        
        # Try different table selectors
        possible_tables = [
            soup.find('table', class_='results'),
            soup.find('table', class_='result'),
            soup.find('table', class_='raceResults'),
            soup.find('table', class_='restab'),
            soup.find('div', class_='results'),
            soup.find('div', class_='result-table')
        ]
        
        results_table = None
        for i, table in enumerate(possible_tables):
            if table:
                print(f"Found table with selector {i}")
                results_table = table
                break
        
        # If no specific table found, look for any table
        if not results_table:
            all_tables = soup.find_all('table')
            print(f"Found {len(all_tables)} tables on the page")
            
            if all_tables:
                for i, table in enumerate(all_tables):
                    print(f"Table {i}: {table.get('class', 'no class')}")
                    # Look for tables that might contain results
                    if any(word in str(table).lower() for word in ['rider', 'time', 'team', 'position']):
                        print(f"Table {i} seems to contain race data")
                        results_table = table
                        break
        
        if not results_table:
            print("No results table found. This might mean:")
            print("1. The race hasn't finished yet")
            print("2. Results aren't published yet")
            print("3. The page structure has changed")
            print("4. The URL might be incorrect")
            
            # Show what content we did find
            print("\nContent preview:")
            text_content = soup.get_text()[:500]
            print(text_content)
            return None
        
        print("Processing results table...")
        
        # Extract table headers
        headers_row = results_table.find('thead') or results_table.find('tr')
        if headers_row:
            headers = [th.text.strip() for th in headers_row.find_all(['th', 'td'])]
            print(f"Found headers: {headers}")
        else:
            headers = ['Position', 'Rider', 'Team', 'Time', 'Points']
            print("Using default headers")
        
        # Extract table data
        results = []
        tbody = results_table.find('tbody')
        
        if not tbody:
            # If no tbody, look for all rows
            tbody = results_table
        
        rows = tbody.find_all('tr')
        print(f"Found {len(rows)} rows")
        
        for i, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:  # Ensure we have at least some data
                row_data = []
                for cell in cells:
                    # Extract text with better separation handling
                    text = cell.get_text(separator=' ', strip=True)
                    
                    # Clean up common formatting issues
                    text = text.replace('  ', ' ')  # Replace double spaces
                    text = text.strip()
                    
                    row_data.append(text)
                
                # Skip header rows
                if not any(header_word in str(row_data).lower() for header_word in ['rider', 'time', 'position', 'rank']) or i == 0:
                    results.append(row_data)
                    if i < 3:  # Show first 3 rows for debugging
                        print(f"Row {i}: {row_data}")
        
        print(f"Extracted {len(results)} rows of data")
        
        # Convert to list of dictionaries
        if results:
            # Adjust headers list to match the actual number of columns
            if results and len(results[0]) != len(headers):
                print(f"Adjusting headers from {len(headers)} to {len(results[0])} columns")
                headers = headers[:len(results[0])]  # Trim headers to match data
                if len(headers) < len(results[0]):
                    # Add generic headers if needed
                    for i in range(len(headers), len(results[0])):
                        headers.append(f'Column_{i+1}')
            
            # Convert to list of dictionaries
            results_list = []
            for row in results:
                if len(row) == len(headers):
                    row_dict = dict(zip(headers, row))
                    results_list.append(row_dict)
            
            return results_list
        else:
            print("No results found in the table.")
            return None
            
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        print("This could be due to:")
        print("1. Network connectivity issues")
        print("2. The website blocking the request")
        print("3. The URL being incorrect")
        return None
    except Exception as e:
        print(f"Error parsing the page: {e}")
        print("This could be due to:")
        print("1. Unexpected page structure")
        print("2. Missing HTML elements")
        print("3. JavaScript-rendered content")
        return None

def check_stage_status(url):
    """
    Check if the stage has results or if it's still upcoming
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for indicators of race status
        text_content = soup.get_text().lower()
        
        if 'start time' in text_content and 'finish' not in text_content:
            print("Stage appears to be scheduled but not yet completed")
            return False
        elif 'winner' in text_content or 'results' in text_content:
            print("Stage appears to have results")
            return True
        else:
            print("Stage status unclear")
            return None
            
    except Exception as e:
        print(f"Error checking stage status: {e}")
        return None

def clean_rider_data(results):
    """
    Clean up rider names and team names that might be concatenated
    """
    if not results:
        return results
    
    cleaned_results = []
    
    for row in results:
        cleaned_row = row.copy()
        
        # Try to identify and clean rider/team columns
        for key, value in row.items():
            if key and 'rider' in key.lower():
                # Try to separate rider name from team name
                # Common patterns: "LastnameFirstnameTeam Name"
                cleaned_value = clean_rider_name(value)
                cleaned_row[key] = cleaned_value
            elif key and 'team' in key.lower():
                # Clean team name
                cleaned_value = clean_team_name(value)
                cleaned_row[key] = cleaned_value
        
        cleaned_results.append(cleaned_row)
    
    return cleaned_results

def clean_rider_name(name_text):
    """
    Extract rider name from concatenated rider+team text
    """
    if not name_text:
        return name_text
    
    # Common team name patterns to remove
    team_patterns = [
        'Alpecin', 'Deceuninck', 'Quick-Step', 'Jumbo-Visma', 'UAE Team Emirates',
        'INEOS Grenadiers', 'Bahrain Victorious', 'Trek-Segafredo', 'Lotto',
        'Cofidis', 'Astana', 'Movistar', 'EF Education', 'Bora-hansgrohe',
        'Intermarché', 'Arkéa', 'TotalEnergies', 'Uno-X', 'Groupama-FDJ'
    ]
    
    # Try to find where team name starts
    for pattern in team_patterns:
        if pattern in name_text:
            # Split at the team name
            parts = name_text.split(pattern)
            if len(parts) > 1:
                rider_part = parts[0].strip()
                # Try to separate first and last name
                if len(rider_part) > 2:
                    return format_rider_name(rider_part)
    
    # If no team pattern found, try other methods
    return format_rider_name(name_text)

def format_rider_name(name_text):
    """
    Format rider name to "Firstname Lastname" format
    """
    if not name_text:
        return name_text
    
    # Remove common suffixes
    name_text = name_text.replace('Jr.', '').replace('Sr.', '').strip()
    
    # Try to identify where firstname ends and lastname begins
    # This is tricky without a database, but we can make some assumptions
    
    # If it's already properly formatted, return as-is
    if ' ' in name_text and len(name_text.split(' ')) == 2:
        return name_text
    
    # If no spaces, try to split CamelCase
    if ' ' not in name_text:
        # Look for uppercase letters that might indicate name boundaries
        import re
        
        # Split on uppercase letters (but keep them)
        parts = re.findall(r'[A-Z][a-z]*', name_text)
        
        if len(parts) >= 2:
            # Assume last part is surname, everything else is given name
            given_name = ' '.join(parts[:-1])
            surname = parts[-1]
            return f"{given_name} {surname}"
    
    return name_text

def clean_team_name(team_text):
    """
    Clean team name
    """
    if not team_text:
        return team_text
    
    # Remove rider name if it's concatenated
    # This is harder to do reliably, so we'll do basic cleanup
    team_text = team_text.strip()
    
    # Remove common prefixes that might be rider names
    import re
    
    # If it starts with what looks like a name (CamelCase), try to extract team
    if re.match(r'^[A-Z][a-z]+[A-Z][a-z]+', team_text):
        # Find team name patterns
        team_patterns = [
            'Alpecin - Deceuninck', 'Quick-Step Alpha Vinyl', 'Jumbo-Visma',
            'UAE Team Emirates', 'INEOS Grenadiers', 'Bahrain Victorious',
            'Trek-Segafredo', 'Lotto Dstny', 'Cofidis', 'Astana Qazaqstan',
            'Movistar Team', 'EF Education-EasyPost', 'Bora-hansgrohe',
            'Intermarché-Circus-Wanty', 'Arkéa-Samsic', 'TotalEnergies',
            'Uno-X Pro Cycling', 'Groupama-FDJ'
        ]
        
        for pattern in team_patterns:
            if pattern in team_text:
                return pattern
    
    return team_text
    """
    Save results to CSV file
    """
    if not results:
        print("No results to save")
        return
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        
        print(f"💾 Results saved to {filename}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def display_results(results, max_rows=None):
    """
    Display results in a formatted table
    """
    if not results:
        print("No results to display")
        return
    
    # Limit results if specified
    if max_rows:
        results = results[:max_rows]
    
    # Get column names
    headers = list(results[0].keys())
    
    # Calculate column widths
    col_widths = {}
    for header in headers:
        col_widths[header] = len(header)
        for row in results:
            if len(str(row.get(header, ''))) > col_widths[header]:
                col_widths[header] = len(str(row.get(header, '')))
    
    # Print header
    header_line = " | ".join(header.ljust(col_widths[header]) for header in headers)
    print(header_line)
    print("-" * len(header_line))
    
    # Print rows
    for row in results:
        row_line = " | ".join(str(row.get(header, '')).ljust(col_widths[header]) for header in headers)
        print(row_line)

def main():
    """
    Main function to run the scraper
    """
    url = "https://www.procyclingstats.com/race/tour-de-france/2025/stage-4"
    
    print("=" * 60)
    print("Tour de France 2025 Stage 1 Results Scraper")
    print("=" * 60)
    print(f"URL: {url}")
    print("-" * 60)
    
    # First check if the stage has results
    print("Checking stage status...")
    stage_status = check_stage_status(url)
    
    if stage_status is False:
        print("\n⚠️  WARNING: This stage appears to be scheduled but not yet completed.")
        print("The results may not be available yet.")
        print("Please check back after the stage has finished.")
        
        user_input = input("\nDo you want to continue anyway? (y/n): ")
        if user_input.lower() != 'y':
            print("Exiting...")
            return
    
    print("\nAttempting to scrape results...")
    
    # Scrape the results
    results = scrape_tour_de_france_stage(url)
    
    if results:
        print(f"\n✅ Successfully scraped {len(results)} results!")
        
        # Clean up the data
        print("Cleaning up rider and team names...")
        cleaned_results = clean_rider_data(results)
        
        print("\nStage Results:")
        print("=" * 60)
        display_results(cleaned_results)
        
        # Save to CSV
        csv_filename = "tour_de_france_2025_stage_1_results.csv"
        save_to_csv(cleaned_results, csv_filename)
        
        # Display top 10 results if there are more than 10
        if len(cleaned_results) > 10:
            print("\nTop 10 Results:")
            print("-" * 40)
            display_results(cleaned_results, 10)
        
    else:
        print("\n❌ Failed to scrape results.")
        print("\nPossible reasons:")
        print("1. The stage hasn't finished yet")
        print("2. Results aren't published yet")
        print("3. The page structure has changed")
        print("4. The website is blocking requests")
        print("\nTry again later or check the URL manually in your browser.")

if __name__ == "__main__":
    main()