# utils/youtube.py
import yt_dlp
import logging
import os
from config import MAX_FILESIZE_MB

logger = logging.getLogger(__name__)

def get_video_info(video_url, max_retries=3):
    """
    Extract video information using yt-dlp with retry logic
    """
    retries = 0
    while retries < max_retries:
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    raise ValueError("Could not retrieve video information")
                
                # Format the video information
                formats = []
                # Filter formats - prioritize progressive formats (video+audio)
                for format in info.get('formats', []):
                    # Skip formats without resolution or filesize info
                    if (not format.get('height') or 
                        format.get('filesize') is None and format.get('filesize_approx') is None):
                        continue
                        
                    # Get filesize (or approximate)
                    filesize = format.get('filesize')
                    if filesize is None:
                        filesize = format.get('filesize_approx', 0)
                    
                    # Convert to MB for readability
                    filesize_mb = filesize / (1024 * 1024)
                    
                    # Skip extremely large files
                    if filesize_mb > MAX_FILESIZE_MB * 2:  # Allow some buffer
                        continue
                        
                    # Create a readable format name
                    if format.get('height'):
                        resolution = f"{format.get('height')}p"
                    else:
                        resolution = "Audio Only"
                        
                    format_name = f"{resolution} ({format.get('ext')})"
                    if format.get('vcodec') != 'none' and format.get('acodec') != 'none':
                        format_name += " [Video+Audio]"
                    elif format.get('acodec') != 'none':
                        format_name += " [Audio]"
                        
                    formats.append({
                        'format_id': format['format_id'],
                        'format_name': format_name,
                        'resolution': resolution,
                        'ext': format['ext'],
                        'url': format.get('url'),
                        'filesize': filesize_mb
                    })
                
                # Sort by quality (resolution)
                formats.sort(key=lambda x: (
                    0 if 'p' in x.get('resolution', '') else 1,  # Videos first
                    -int(x.get('resolution', '0').replace('p', '')) if 'p' in x.get('resolution', '') else 0  # Higher resolution first
                ))
                
                # Limit to top formats to avoid cluttering the message
                formats = formats[:5]
                
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'channel': info.get('channel'),
                    'duration': info.get('duration'),
                    'formats': formats
                }
                
        except Exception as e:
            logger.warning(f"Attempt {retries+1} failed: {str(e)}")
            retries += 1
            if retries >= max_retries:
                logger.error(f"All {max_retries} attempts failed for URL: {video_url}")
                raise
    
    raise Exception("Failed to extract video information after multiple attempts")

def extract_video_id(url):
    """
    Extract YouTube video ID from various URL formats
    """
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            return info_dict.get('id')
    except Exception as e:
        logger.error(f"Failed to extract video ID: {str(e)}")
        return None