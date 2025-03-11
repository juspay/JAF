from enum import Enum



class PipelineTypeEnum(Enum):
    SETUP_PIPELINE = "setup_pipeline"
    INDEX_PIPELINE = "index_pipeline"
    RAG_PIPELINE = "rag_pipeline"
    CHAT_PIPELINE = "chat_pipeline"
    AGENT_PIPELINE = "agent_pipline"
    MULTI_AGENT_PIPELINE = "multi_agent_pipeline"
    SUMMARIZE_PIPELINE = "summarize_pipeline"
    CUSTOM_PIPELINE = "custom_pipeline"
    CODE_COMMENT_PIPELINE = "code_comment_pipeline"
    CODE_REFACTOR_PIPELINE = "code_refactor_pipeline"
    CODE_GIT_DIFF_REVIEW_PIPELINE = "code_git_diff_review_pipeline"
    COMMENT_EMBED_PIPELINE = "comment_embed_pipeline"
    COMMENT_SEARCH_PIPELINE = "comment_search_pipeline"
    RUST_MIGRATION_PIPELINE = "rust_migration_pipeline"
