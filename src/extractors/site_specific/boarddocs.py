"""BoardDocs special collection with year navigation."""
import re
from typing import List
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ..date_parser import extract_date_from_text
from ..dom_utils import extract_text_from_element


async def collect_boarddocs_html(browser_manager, base_url: str, start_date: str = None, end_date: str = None) -> List[str]:
    """Collect HTML from BoardDocs by clicking through Meetings tab and years."""
    htmls = []
    page = None
    
    try:
        page = await browser_manager.new_page()
        
        print("Navigating to BoardDocs...")
        await page.goto(base_url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)  # Wait for JavaScript to load
        
        # Click on "Meetings" tab to show all meetings
        print("Clicking 'Meetings' tab...")
        meetings_clicked = False
        meetings_selectors = [
            '#ui-id-3',  # Direct ID for Meetings tab link
            'a[href="#tab-meetings"]',  # href selector
            'li#li-meetings a',  # Tab list item
            'a:has-text("Meetings")',
            '[aria-label*="Meetings"]',
            '#mainMeetings',
        ]
        
        for selector in meetings_selectors:
            try:
                meetings_tab = await page.query_selector(selector)
                if meetings_tab:
                    is_visible = await meetings_tab.is_visible()
                    if is_visible:
                        await meetings_tab.click()
                        await page.wait_for_timeout(3000)
                        print(f"Clicked 'Meetings' tab using: {selector}")
                        meetings_clicked = True
                        break
            except:
                continue
        
        if not meetings_clicked:
            print("Could not find 'Meetings' tab, using default view")
        
        # Wait for meetings to load after clicking the tab
        await page.wait_for_timeout(3000)
        
        # Wait for jQuery UI accordion to initialize
        try:
            await page.evaluate("""
                () => new Promise((resolve) => {
                    const checkAccordion = () => {
                        const accordion = document.getElementById('meeting-accordion');
                        if (accordion && accordion.classList.contains('ui-accordion')) {
                            resolve();
                        } else {
                            setTimeout(checkAccordion, 500);
                        }
                    };
                    setTimeout(() => resolve(), 10000); // Timeout after 10s
                    checkAccordion();
                })
            """)
            print("jQuery UI accordion initialized")
        except:
            print("Could not confirm accordion initialization")
        
        await page.wait_for_timeout(2000)
        
        # Ensure the meetings pane is visible and scroll to it
        try:
            meetings_pane = await page.query_selector('#wrap-meetings')
            if meetings_pane:
                await meetings_pane.scroll_into_view_if_needed()
                await page.wait_for_timeout(2000)
                print("Scrolled to meetings pane")
        except:
            print("Could not scroll to meetings pane")
        
        # Wait for the accordion or meetings list to be ready
        try:
            # Try multiple possible selectors
            selectors_to_try = ['#meeting-accordion', '#meetings', 'div.pane-wrap']
            for sel in selectors_to_try:
                element = await page.query_selector(sel)
                if element:
                    print(f"Found element: {sel}")
                    break
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Warning: {e}")
        
        # Debug: Check what's visible
        try:
            meeting_count = await page.locator('a.icon.prevnext.meeting').count()
            print(f"Visible meetings on page: {meeting_count}")
            
            # Try to find year elements using simpler selector
            year_elements = await page.query_selector_all('xpath=//a[text()="2025" or text()="2024" or text()="2023"]')
            print(f"Found {len(year_elements)} year links")
        except Exception as e:
            print(f"Debug error: {e}")
        
        # Find and click on year tabs to load meetings for each year
        years_to_check = []
        if start_date and end_date:
            from datetime import datetime
            start_year = datetime.strptime(start_date, '%Y-%m-%d').year
            end_year = datetime.strptime(end_date, '%Y-%m-%d').year
            years_to_check = list(range(end_year, start_year - 1, -1))  # Descending order (2025, 2024, ...)
        else:
            # Default: check last 3 years
            from datetime import datetime
            current_year = datetime.now().year
            years_to_check = [current_year, current_year - 1, current_year - 2]
        
        print(f"Will expand years: {years_to_check}")
        
        # Wait a bit for the meetings pane to load
        await page.wait_for_timeout(2000)
        
        # Expand all years
        for year in years_to_check:
            try:
                print(f"Looking for year {year}...")
                
                # Try using JavaScript to find and click the year accordion section
                try:
                    result = await page.evaluate(f"""
                        () => {{
                            // Find all accordion headers
                            const sections = document.querySelectorAll('section.ui-accordion-header');
                            console.log('Found sections:', sections.length);
                            
                            // Find the section for this year
                            for (const section of sections) {{
                                // The <a> with class 'lefMenu' is a direct child of the section
                                const link = section.querySelector('a.lefMenu');
                                const text = link ? link.textContent.trim() : '';
                                console.log('Section text:', text);
                                
                                if (text === "{year}") {{
                                    console.log('Clicking year {year}');
                                    // Click the section itself, not the link
                                    section.click();
                                    return {{ clicked: true, text: text }};
                                }}
                            }}
                            return {{ clicked: false, sectionCount: sections.length }};
                        }}
                    """)
                    
                    print(f"JavaScript result: {result}")
                    
                    if result.get('clicked'):
                        print(f"Clicked year {year} using JavaScript")
                        await page.wait_for_timeout(3000)
                        
                        # Check how many meetings are now visible
                        meeting_count = await page.locator('a.icon.prevnext.meeting').count()
                        print(f"After clicking {year}: {meeting_count} meetings visible")
                    else:
                        section_count = result.get('sectionCount', 0)
                        print(f"JavaScript found {section_count} sections but none matched year {year}")
                except Exception as e:
                    print(f"JavaScript method failed for year {year}: {e}")
                    
            except Exception as year_error:
                print(f"Error processing year {year}: {year_error}")
                continue
        
        # Extract meeting data directly from the live DOM using JavaScript
        # Query ALL meetings from ALL sections (Featured + all year sections)
        # Don't rely on visibility since accordion sections toggle
        print("Extracting meeting data from live DOM...")
        meetings_data = await page.evaluate("""
            () => {
                const meetings = [];
                const seenIds = new Set();
                
                // Debug: Log what we find
                const debug = [];
                
                // Find all sections (Featured + year sections)
                const featuredSection = document.querySelector('div.wrap-featured');
                const yearSections = document.querySelectorAll('div.wrap-year');
                
                debug.push(`Featured section: ${featuredSection ? 'found' : 'NOT FOUND'}`);
                debug.push(`Year sections: ${yearSections.length} found`);
                
                const sections = [featuredSection, ...Array.from(yearSections)];
                
                sections.forEach((section, index) => {
                    if (!section) {
                        debug.push(`Section ${index}: NULL`);
                        return;
                    }
                    
                    // Find all meeting links in this section
                    const meetingLinks = section.querySelectorAll('a.icon.prevnext.meeting');
                    debug.push(`Section ${index}: ${meetingLinks.length} meetings`);
                    
                    meetingLinks.forEach(link => {
                        const id = link.id || link.getAttribute('unique');
                        
                        // Skip duplicates
                        if (!id || seenIds.has(id)) return;
                        seenIds.add(id);
                        
                        // Get all divs inside the link - first is date, second is name, optional third is committee
                        const allDivs = link.querySelectorAll('div');
                        
                        if (allDivs.length >= 2) {
                            // Find date (has <strong> tag) and name (plain text)
                            let dateText = '';
                            let nameText = '';
                            let committeeText = '';
                            
                            // First div usually contains the date with <strong>
                            const strongTag = allDivs[0].querySelector('strong');
                            if (strongTag) {
                                dateText = strongTag.textContent.trim();
                                nameText = allDivs[1].textContent.trim();
                                if (allDivs.length >= 3) {
                                    committeeText = allDivs[2].textContent.trim();
                                }
                            } else {
                                // Fallback: first div is date, second is name
                                dateText = allDivs[0].textContent.trim();
                                nameText = allDivs[1].textContent.trim();
                                if (allDivs.length >= 3) {
                                    committeeText = allDivs[2].textContent.trim();
                                }
                            }
                            
                            const meeting = {
                                id: id,
                                date: dateText,
                                name: nameText,
                                committee: committeeText || null
                            };
                            meetings.push(meeting);
                        } else {
                            debug.push(`  Meeting ${id}: only ${allDivs.length} divs found`);
                        }
                    });
                });
                
                console.log('Debug info:', debug.join(' | '));
                return { meetings, debug };
            }
        """)
        
        debug_info = meetings_data.get('debug', [])
        print(f"JavaScript debug: {' | '.join(debug_info) if debug_info else 'No debug info'}")
        
        meetings_list = meetings_data.get('meetings', [])
        print(f"Extracted {len(meetings_list)} meetings from live DOM")
        
        # Store the extracted data as a special HTML-like format that our parser can read
        # We'll encode it as JSON in a special marker
        import json
        html = f"<!-- BOARDDOCS_MEETINGS_DATA:{json.dumps(meetings_list)} -->"
        htmls.append(html)
        print(f"Total: Collected meeting data from all expanded sections")
        
    except Exception as e:
        print(f"Error collecting BoardDocs HTML: {e}")
    finally:
        if page:
            try:
                await page.close()
            except:
                pass
    
    return htmls


def extract_boarddocs_meetings(soup: BeautifulSoup, base_url: str) -> List[MeetingMetadata]:
    """Extract meetings from BoardDocs platform."""
    meetings = []
    seen_ids = set()  # Track unique meeting IDs to avoid duplicates
    
    # Check if we have the special JSON format from JavaScript extraction
    import json
    import re
    html_text = str(soup)
    json_match = re.search(r'<!-- BOARDDOCS_MEETINGS_DATA:(.*?) -->', html_text, re.DOTALL)
    
    if json_match:
        # Parse meetings from JSON data extracted via JavaScript
        print("Using JavaScript-extracted meeting data")
        try:
            meetings_data = json.loads(json_match.group(1))
            print(f"Found {len(meetings_data)} meetings in JSON data")
            
            for meeting_data in meetings_data:
                meeting_id = meeting_data.get('id')
                if not meeting_id or meeting_id in seen_ids:
                    continue
                
                seen_ids.add(meeting_id)
                
                # Parse date
                date_text = meeting_data.get('date', '')
                date = extract_date_from_text(date_text)
                
                # Build title
                title = meeting_data.get('name', '')
                committee = meeting_data.get('committee')
                if committee:
                    title = f"{committee} - {title}"
                
                if not title or not date:
                    continue
                
                # Construct URLs
                # For BoardDocs, all documents are accessed through the meeting detail page
                meeting_url = f"{base_url}?open&id={meeting_id}"
                
                # Note: BoardDocs requires navigating to the meeting page to access agenda/minutes
                # The agenda and minutes are available as buttons on the meeting detail page
                # We set these to None since they're not direct links (accessed via meeting page)
                agenda_url = None
                minutes_url = None
                
                meeting = MeetingMetadata()
                meeting.title = title
                meeting.date = date
                meeting.meeting_url = meeting_url
                meeting.agenda_url = agenda_url
                meeting.minutes_url = minutes_url
                meetings.append(meeting)
            
            print(f"Extracted {len(meetings)} unique meetings from JSON data")
            return meetings
            
        except Exception as e:
            print(f"Error parsing JSON data: {e}")
            # Fall through to HTML parsing
    
    # Fallback: Parse from HTML (for backward compatibility)
    print("Using HTML parsing (fallback)")
    meeting_links = soup.find_all('a', class_='icon prevnext meeting')
    print(f"Found {len(meeting_links)} total meeting links in HTML")
    
    # Debug: Check which sections contain meetings
    try:
        featured_section = soup.find('div', class_='wrap-featured')
        if featured_section:
            featured_meetings = featured_section.find_all('a', class_='icon prevnext meeting')
            print(f"  - Featured section: {len(featured_meetings)} meetings")
        
        year_sections = soup.find_all('div', class_='wrap-year')
        print(f"  - Found {len(year_sections)} year sections")
        for year_section in year_sections:
            year = year_section.get('year', 'unknown')
            year_meetings = year_section.find_all('a', class_='icon prevnext meeting')
            print(f"  - Year {year}: {len(year_meetings)} meetings")
    except Exception as debug_e:
        print(f"Debug error: {debug_e}")
    
    for link in meeting_links:
        # Get unique meeting ID to avoid duplicates
        meeting_id = link.get('id') or link.get('unique')
        if meeting_id in seen_ids:
            continue  # Skip duplicates
        
        # Extract date from div with class='date'
        date_div = link.find('div', class_='date')
        if not date_div:
            continue
        
        date_text = extract_text_from_element(date_div)
        date = extract_date_from_text(date_text)
        
        # Extract title from div with class='name'
        name_div = link.find('div', class_='name')
        if not name_div:
            continue
        
        title = extract_text_from_element(name_div)
        
        # Extract committee name (optional)
        committee_div = link.find('div', class_='committeename')
        if committee_div:
            committee = extract_text_from_element(committee_div)
            title = f"{committee} - {title}"
        
        if not title or not date:
            continue
        
        # Construct meeting URL and agenda PDF URL
        if meeting_id:
            seen_ids.add(meeting_id)  # Mark as seen
            
            meeting_url = f"{base_url}?open&id={meeting_id}"
            
            # Construct agenda PDF download URL based on BoardDocs API
            # Format: https://go.boarddocs.com/ca/acoe/Board.nsf/goto?open&id=MEETING_ID
            parsed = urlparse(base_url)
            base_path = parsed.path.rsplit('/', 1)[0]  # Remove /Public to get /Board.nsf
            agenda_url = f"{parsed.scheme}://{parsed.netloc}{base_path}/goto?open&id={meeting_id}"
        else:
            meeting_url = None
            agenda_url = None
        
        meeting = MeetingMetadata()
        meeting.title = title
        meeting.date = date
        meeting.meeting_url = meeting_url
        meeting.agenda_url = agenda_url
        # Note: Minutes URL would require clicking into the meeting and checking for btn-view-minutes
        # For now, we'll leave it as None since it requires additional navigation
        
        meetings.append(meeting)
    
    print(f"Extracted {len(meetings)} unique meetings")
    return meetings


def should_use_boarddocs_extractor(base_url: str) -> bool:
    """Check if BoardDocs extractor should be used."""
    return 'boarddocs.com' in base_url.lower()
