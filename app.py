import os
import logging
import streamlit as st
from dotenv import load_dotenv
from rag_engine import RAGEngine

# Load environment variables
load_dotenv()

# Configure logging - must happen before other imports
log_level = os.getenv("LOG_LEVEL", "INFO")

# Clear existing handlers to avoid duplicates
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configure with both console and file output
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rag_app.log', mode='a')
    ],
    force=True  # Force reconfiguration
)
logger = logging.getLogger(__name__)
logger.info("=" * 60)
logger.info("Application started")
logger.info("=" * 60)

# Page configuration
st.set_page_config(
    page_title="PDF RAG Chat",
    page_icon="📚",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "rag_engine" not in st.session_state:
    # Initialize RAG engine
    try:
        logger.info("Initializing RAG engine from Streamlit")
        st.session_state.rag_engine = RAGEngine(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            pdf_directory=os.getenv("PDF_DIRECTORY", "./pdfs")
        )
        st.session_state.engine_initialized = True
        logger.info("RAG engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG engine: {str(e)}", exc_info=True)
        st.session_state.engine_initialized = False
        st.session_state.init_error = str(e)

if "indexed" not in st.session_state:
    st.session_state.indexed = False

# App title
st.title("📚 PDF RAG Chat Assistant")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    # Check if engine is initialized
    if not st.session_state.get("engine_initialized", False):
        st.error("❌ Failed to initialize RAG engine")
        st.error(f"Error: {st.session_state.get('init_error', 'Unknown error')}")
        st.info("Please check your .env file and ensure all credentials are set correctly.")
        st.stop()

    # Get stats
    try:
        stats = st.session_state.rag_engine.get_stats()
        logger.debug(f"Stats: {stats}")
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        stats = {"pdf_files": 0, "total_chunks": 0}

    st.metric("PDF Files", stats["pdf_files"])
    st.metric("Indexed Chunks", stats["total_chunks"])

    st.divider()

    # Debug mode toggle
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False

    if st.checkbox("🐛 Debug Mode", value=st.session_state.debug_mode):
        st.session_state.debug_mode = True
        st.info("Debug mode enabled - check rag_app.log for detailed logs")

        # Set all loggers to DEBUG
        logging.getLogger().setLevel(logging.DEBUG)
        for name in logging.root.manager.loggerDict:
            logging.getLogger(name).setLevel(logging.DEBUG)
    else:
        st.session_state.debug_mode = False
        # Reset to INFO level
        logging.getLogger().setLevel(logging.INFO)
        for name in logging.root.manager.loggerDict:
            logging.getLogger(name).setLevel(logging.INFO)

    st.divider()

    # Auto-index on first load
    if not st.session_state.indexed:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total, message):
            if total > 0:
                progress = min(current / total, 1.0)
                progress_bar.progress(progress)
                status_text.text(message)

        files, chunks = st.session_state.rag_engine.index_documents(progress_callback=update_progress)
        st.session_state.indexed = True

        progress_bar.empty()
        status_text.empty()

        if files > 0 and chunks > 0:
            st.success(f"✅ Indexed {files} new files ({chunks} chunks)")
        elif files > 0 and chunks == 0:
            st.error("❌ PDFs were found but no text could be extracted")
            st.error("Your PDFs appear to be scanned images (no text layer)")
            st.info("💡 **Solution**: Use OCR tools to convert scanned PDFs to searchable PDFs:")
            st.markdown("""
            - **Adobe Acrobat DC** - Export PDF > OCR Text Recognition
            - **Online OCR**: [ocr.space](https://ocr.space), [ilovepdf.com](https://www.ilovepdf.com/ocr-pdf)
            - **Open Source**: Tesseract OCR with `ocrmypdf` tool
            """)
        elif stats["total_chunks"] > 0:
            st.info("ℹ️ All PDFs already indexed")
        else:
            st.warning("⚠️ No PDFs found in the directory")

    # Manual re-index button
    st.subheader("📥 Index Management")

    if st.button("🔄 Re-index All PDFs", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total, message):
            if total > 0:
                progress = min(current / total, 1.0)
                progress_bar.progress(progress)
                status_text.text(message)

        files, chunks = st.session_state.rag_engine.index_documents(force_reindex=True, progress_callback=update_progress)

        progress_bar.empty()
        status_text.empty()
        st.success(f"✅ Re-indexed {files} files ({chunks} chunks)")
        st.rerun()

    if st.button("🔍 Check for New PDFs", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total, message):
            if total > 0:
                progress = min(current / total, 1.0)
                progress_bar.progress(progress)
                status_text.text(message)

        files, chunks = st.session_state.rag_engine.index_documents(progress_callback=update_progress)

        progress_bar.empty()
        status_text.empty()

        if files > 0:
            st.success(f"✅ Indexed {files} new files ({chunks} chunks)")
            st.rerun()
        else:
            st.info("ℹ️ No new PDFs to index")

    st.divider()

    # Clear chat button
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Instructions
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. Place PDF files in the `pdfs/` directory
        2. Click "Check for New PDFs" or restart the app
        3. Ask questions about your documents
        4. View sources for each answer

        **Tips:**
        - Be specific in your questions
        - The AI only uses information from your PDFs
        - Check the sources to verify answers
        """)

# Main chat interface
st.subheader("💬 Chat")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display sources if available
        if message["role"] == "assistant" and "sources" in message:
            if message["sources"]:
                with st.expander(f"📄 View {len(message['sources'])} sources"):
                    for idx, source in enumerate(message["sources"], 1):
                        st.markdown(f"**Source {idx}: {source['file_name']}** (chunk {source['chunk_index']})")
                        st.markdown(f"_{source['content']}_")
                        st.divider()

# Check if there are any indexed documents
if stats["total_chunks"] == 0:
    st.warning("⚠️ No documents indexed yet. Please add PDF files to the `pdfs/` directory and click 'Check for New PDFs'.")
else:
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response from RAG engine
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    logger.info(f"Processing user query: {prompt[:100]}...")
                    result = st.session_state.rag_engine.query(prompt)
                    logger.info("Query processed successfully")

                    # Display answer
                    st.markdown(result["answer"])

                    # Display sources
                    if result["sources"]:
                        with st.expander(f"📄 View {len(result['sources'])} sources"):
                            for idx, source in enumerate(result["sources"], 1):
                                st.markdown(f"**Source {idx}: {source['file_name']}** (chunk {source['chunk_index']})")
                                st.markdown(f"_{source['content']}_")
                                st.divider()

                    # Add assistant message to chat
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result["sources"]
                    })

                except Exception as e:
                    logger.error(f"Error processing query: {str(e)}", exc_info=True)
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)

                    if st.session_state.debug_mode:
                        st.exception(e)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "sources": []
                    })

# Footer
st.divider()
st.caption("Powered by OpenAI GPT-4o-mini and Supabase Vector Database")
