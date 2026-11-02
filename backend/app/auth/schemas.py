from pydantic import BaseModel, Field

OAUTH_PARAM_MAX = 2048


class OAuthAuthorizeRequest(BaseModel):
    redirect_uri: str = Field(max_length=OAUTH_PARAM_MAX)


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str


class OAuthCallbackRequest(BaseModel):
    code: str = Field(max_length=OAUTH_PARAM_MAX)
    state: str = Field(max_length=OAUTH_PARAM_MAX)
    redirect_uri: str = Field(max_length=OAUTH_PARAM_MAX)
