from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel, Field
from core.config import settings

DataT = TypeVar('DataT')

class Message(BaseModel):
    """
    Schema for a generic message response.

    :param message: The message content.
    :type message: str
    """
    message: str

class Pagination(BaseModel):
    """
    Schema for pagination metadata.

    :param page: Current page number.
    :type page: int
    :param page_size: Number of items per page.
    :type page_size: int
    :param total_items: Total number of items available.
    :type total_items: int
    :param total_pages: Total number of pages.
    :type total_pages: int
    """
    page: int
    page_size: int
    total_items: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Generic schema for a paginated response.

    :param data: List of data items for the current page.
    :type data: List[DataT]
    :param pagination: Pagination metadata.
    :type pagination: Pagination
    """
    data: List[DataT]
    pagination: Pagination

class CommonQueryParameters(BaseModel):
    """
    Common query parameters for pagination.

    :param page: Page number, defaults to `settings.DEFAULT_PAGE`.
    :type page: int
    :param page_size: Number of items per page, defaults to `settings.DEFAULT_PAGE_SIZE`,
                      max value `settings.MAX_PAGE_SIZE`.
    :type page_size: int
    """
    page: int = Field(settings.DEFAULT_PAGE, ge=1, description="Page number")
    page_size: int = Field(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page")
