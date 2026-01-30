#!/usr/bin/env python3
"""
OmniCast - Multi-Format News Distribution Platform
Main entry point for running the application
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Run the OmniCast server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n" + "=" * 60)
        print("WARNING: OPENAI_API_KEY environment variable not set!")
        print("The platform requires an OpenAI API key for full functionality.")
        print("Set it in your .env file or environment variables.")
        print("=" * 60 + "\n")

    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ██████╗ ███╗   ███╗███╗   ██╗██╗ ██████╗ █████╗ ███████╗║
    ║  ██╔═══██╗████╗ ████║████╗  ██║██║██╔════╝██╔══██╗██╔════╝║
    ║  ██║   ██║██╔████╔██║██╔██╗ ██║██║██║     ███████║███████╗║
    ║  ██║   ██║██║╚██╔╝██║██║╚██╗██║██║██║     ██╔══██║╚════██║║
    ║  ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║╚██████╗██║  ██║███████║║
    ║   ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝║
    ║                                                           ║
    ║   Multi-Format News Distribution Platform                 ║
    ║                                                           ║
    ╠═══════════════════════════════════════════════════════════╣
    ║                                                           ║
    ║   Server starting at: http://{host}:{port:<5}                ║
    ║                                                           ║
    ║   Features:                                               ║
    ║   • TV Broadcast Scripts                                  ║
    ║   • Web Articles (SEO-optimized)                          ║
    ║   • Social Media Videos (with overlays & captions)        ║
    ║   • YouTube Content (thumbnails, descriptions)            ║
    ║   • Podcast Audio (with TTS narration)                    ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
