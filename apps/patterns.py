drive_patterns = [
    # Matches file links with "file/d/<file_id>/view"
                r'https://drive\.google\.com/file/d/.*?/view\?usp=sharing',
                r'https://drive\.google\.com/file/d/.*?/view',
                
                # Matches links with "open?id=<file_id>"
                r'https://drive\.google\.com/open\?id=.*',
                
                # Matches general Google Docs links
                r'https://docs\.google\.com/.*',

                # Matches direct download links with "uc?id=<file_id>&export=download"
                r'https://drive\.google\.com/uc\?id=.*&export=download',

                # Matches Google Drive folder links
                r'https://drive\.google\.com/drive/folders/.*\?usp=sharing',
                r'https://drive\.google\.com/drive/folders/.*',

                # Matches shortened Google Drive links
                r'https://drive\.google\.com/shortcuts/.*',
                
                # Matches general shared links (e.g., with "sharing" parameter)
                r'https://drive\.google\.com/.*\?usp=sharing',
                r'https://drive\.google\.com/.*\?usp=drive_link',
            ]