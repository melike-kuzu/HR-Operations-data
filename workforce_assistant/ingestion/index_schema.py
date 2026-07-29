from __future__ import annotations

from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)


VECTOR_DIMENSIONS = 1536
VECTOR_PROFILE_NAME = "workforce-vector-profile"
VECTOR_ALGORITHM_NAME = "workforce-hnsw"
SEMANTIC_CONFIGURATION_NAME = "workforce-semantic-config"


INDEX_FIELDS = [
    "id",
    "record_type",
    "consultant_id",
    "consultant_name",
    "content",
    "content_vector",
    "title",
    "source_type",
    "source_file",
    "sheet_name",
    "row_number",
    "skills",
    "level",
    "group",
    "client",
    "page_number",
    "chunk_id",
    "is_active",
    "last_modified",
]


def build_workforce_index(index_name: str) -> SearchIndex:
    """
    Build the Azure AI Search index used by the workforce assistant.

    The index stores searchable consultant profiles, skill records,
    experience records and approved document chunks.

    Exact operational values such as utilisation, availability and
    allocation continue to come from structured parquet/SQL sources.
    """

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="record_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="consultant_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="consultant_name",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            sortable=True,
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.Single
            ),
            searchable=True,
            vector_search_dimensions=VECTOR_DIMENSIONS,
            vector_search_profile_name=VECTOR_PROFILE_NAME,
        ),
        SearchField(
            name="skills",
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.String
            ),
            searchable=True,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="level",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="group",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="client",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="source_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="source_file",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="sheet_name",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="row_number",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="page_number",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="is_active",
            type=SearchFieldDataType.Boolean,
            filterable=True,
        ),
        SimpleField(
            name="last_modified",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=VECTOR_ALGORITHM_NAME,
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE_NAME,
                algorithm_configuration_name=VECTOR_ALGORITHM_NAME,
            )
        ],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIGURATION_NAME,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(
                        field_name="title",
                    ),
                    content_fields=[
                        SemanticField(
                            field_name="content",
                        ),
                    ],
                    keywords_fields=[
                        SemanticField(
                            field_name="consultant_name",
                        ),
                        SemanticField(
                            field_name="client",
                        ),
                    ],
                ),
            )
        ]
    )

    return SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )