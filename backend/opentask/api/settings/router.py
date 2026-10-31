import base64

from fastapi import APIRouter, Depends, HTTPException, UploadFile, BackgroundTasks

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.models.user.schema import AvatarOut, UserOut, UserUpdateIn
from opentask.models.common.response import SuccessResponse
from opentask.repositories.base import AsyncSession, get_session
from opentask.services.settings import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile,
    settings_service: SettingsService = Depends(SettingsService),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[AvatarOut]:

    media = await settings_service.upload_avatar(session, file)
    blob_base64 = base64.b64encode(media.blob).decode("utf-8")
    return SuccessResponse(data=AvatarOut(blob=blob_base64))


@router.get("/avatar")
async def get_avatar(
    settings_service: SettingsService = Depends(SettingsService), session: AsyncSession = Depends(get_session)
) -> SuccessResponse[AvatarOut]:
    media = await settings_service.get_avatar(session)
    if media is None:
        raise HTTPException(status_code=404, detail="No user avatar found")

    blob_base64 = base64.b64encode(media.blob).decode("utf-8")
    return SuccessResponse(data=AvatarOut(blob=blob_base64))


@router.patch("/info")
async def update_info(
    data: UserUpdateIn,
    settings_service: SettingsService = Depends(SettingsService),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[UserOut]:
    user_info = await settings_service.update_user_info(session, data=data)
    return SuccessResponse(data=user_info)


@router.get("/info")
async def get_info(
    settings_service: SettingsService = Depends(SettingsService), session: AsyncSession = Depends(get_session)
) -> SuccessResponse[UserOut]:
    user_info = await settings_service.get_user_info(session)
    return SuccessResponse(data=user_info)


@router.get("/server-config")
async def get_server_config() -> SuccessResponse[dict]:
    """获取服务端配置信息，包括模型配置"""
    from opentask.config import config

    server_config = {
        "default_llm_model": config.default_llm_model,
        "max_tokens": config.max_tokens,
        "available_models": config.available_models,
        "analysis_model": config.analysis_model,
        "chart_generation_model": config.chart_generation_model,
        "sql_generation_model": config.sql_generation_model,
        "openai_base_url": config.openai_base_url,
        # 注意：不返回API密钥，仅用于确认服务端配置已设置
        "has_server_api_key": bool(config.openai_api_key),
        # 添加说明信息，帮助用户了解当前配置
        "model_info": {
            "default_model": config.default_llm_model,
            "provider": "智谱AI (zhipuai)" if "glm" in config.default_llm_model else "OpenAI",
            "description": "当前配置的默认模型"
        }
    }
    return SuccessResponse(data=server_config)


@router.post("/model-selection")
async def update_model_selection(
    model_data: dict,
    current_user: UserModel = Depends(authenticate),
    settings_service: SettingsService = Depends(SettingsService),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[dict]:
    """更新用户选择的模型配置"""
    try:
        # 验证模型选择是否在可用模型列表中
        from opentask.config import config
        selected_model = model_data.get("selected_model")

        if selected_model not in config.available_models:
            raise HTTPException(
                status_code=400,
                detail=f"模型 '{selected_model}' 不在可用模型列表中。可用模型: {', '.join(config.available_models)}"
            )

        # 更新用户的首选模型设置（存储在用户设置中）
        update_data = UserUpdateIn(
            preferred_openai_model=selected_model
        )

        updated_user = await settings_service.update_user_info(session, update_data, str(current_user.id))

        return SuccessResponse(data={
            "message": "模型选择已更新",
            "selected_model": selected_model,
            "provider": "智谱AI (zhipuai)" if "glm" in selected_model else "OpenAI"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新模型选择失败: {str(e)}")
