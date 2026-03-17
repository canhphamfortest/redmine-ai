import streamlit as st
import requests
from datetime import datetime
import time
from streamlit_app.utils.auth import require_login, show_user_header, hide_pages_based_on_auth

st.set_page_config(page_title="LLM Config", page_icon="🤖", layout="wide")

# Hide pages based on authentication status
hide_pages_based_on_auth()

# Show user header FIRST (at top of sidebar)
show_user_header()

# Check authentication
require_login()

API_URL = "http://backend:8000"

st.title("🤖 LLM Configuration")
st.markdown("Configure LLM provider models, pricing, and API keys (OpenAI, Google, Anthropic, Groq)")

# Initialize session state for view mode
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "list"  # "list", "create", "edit"

# Initialize edit config state
if 'edit_config' not in st.session_state:
    st.session_state.edit_config = None

# ===== CONFIG LIST =====
if st.session_state.view_mode == "list":
    st.subheader("Model Pricing Configuration")
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("➕ Create Config", type="primary", use_container_width=True):
            st.session_state.view_mode = "create"
            st.session_state.edit_config = None
            st.rerun()
    
    with col2:
        if st.button("🔄 Sync Default Pricing", use_container_width=True):
            with st.spinner("Syncing default pricing..."):
                try:
                    sync_response = requests.post(
                        f"{API_URL}/api/openai-config/sync-defaults",
                        timeout=30
                    )
                    if sync_response.status_code == 200:
                        st.success("✅ Default pricing synced successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Failed to sync: {sync_response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with col3:
        show_inactive = st.checkbox("Show inactive configs", key="show_inactive_configs")
    
    # Fetch configs
    try:
        params = {"active_only": not show_inactive}
        response = requests.get(f"{API_URL}/api/openai-config", params=params)
        
        if response.status_code == 200:
            configs = response.json()
            
            if not configs:
                st.info("No configs found. Create your first config or sync default pricing.")
            else:
                # Display configs in a table
                st.markdown(f"**Total: {len(configs)} configs**")
                st.markdown("---")
                
                for config in configs:
                    config_id = config.get("id")
                    model_name = config.get("model_name", "")
                    input_price = config.get("input_price_per_1m", 0)
                    output_price = config.get("output_price_per_1m", 0)
                    is_active = config.get("is_active", True)
                    is_default = config.get("is_default", False)
                    description = config.get("description", "")
                    updated_at = config.get("updated_at", "")
                    provider = config.get("provider", "openai")
                    
                    # Convert price per 1M tokens to price per token for display
                    input_price_per_token = input_price
                    output_price_per_token = output_price
                    input_price_display = f"${input_price * 1_000_000:.3f}/1M"
                    output_price_display = f"${output_price * 1_000_000:.3f}/1M"
                    
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2.5, 2, 2, 1.5, 1])
                        
                        with col1:
                            status_icon = "✅" if is_active else "⏸️"
                            default_badge = " ⭐ **Default**" if is_default else ""
                            st.markdown(f"### {status_icon} [{provider}] {model_name}{default_badge}")
                            if description:
                                st.caption(description)
                        
                        with col2:
                            st.markdown("**Input Price:**")
                            st.code(input_price_display)
                            st.caption(f"${input_price_per_token:.9f} per token")
                        
                        with col3:
                            st.markdown("**Output Price:**")
                            st.code(output_price_display)
                            st.caption(f"${output_price_per_token:.9f} per token")
                        
                        with col4:
                            st.markdown("**Updated:**")
                            if updated_at:
                                try:
                                    updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                                    st.caption(updated.strftime('%Y-%m-%d %H:%M'))
                                except:
                                    st.caption(updated_at)
                            else:
                                st.caption("N/A")
                        
                        with col5:
                            # Set as default button or show default badge
                            if is_default:
                                st.markdown("**⭐ Default Model**")
                                st.caption("Currently in use")
                            elif not is_active:
                                st.caption("⚠️ Inactive")
                            else:
                                if st.button("⭐ Set Default", key=f"default_{config_id}"):
                                    with st.spinner("Setting as default model..."):
                                        try:
                                            default_response = requests.post(
                                                f"{API_URL}/api/openai-config/default-model/{model_name}",
                                                params={"provider": provider},
                                                timeout=10
                                            )
                                            if default_response.status_code == 200:
                                                st.success("✅ Model set as default!")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error(f"Failed to set default: {default_response.text}")
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")
                            
                            # Edit button
                            edit_button_key = f"edit_{config_id}"
                            if st.button("✏️ Edit", key=edit_button_key):
                                st.session_state.edit_config = config
                                st.session_state.view_mode = "edit"
                                st.rerun()
                            
                            # Delete button with confirmation
                            delete_confirm_key = f"delete_confirm_{config_id}"
                            if delete_confirm_key not in st.session_state:
                                st.session_state[delete_confirm_key] = False
                            
                            if st.session_state[delete_confirm_key]:
                                st.warning("⚠️ Confirm delete?")
                                col_confirm1, col_confirm2 = st.columns(2)
                                with col_confirm1:
                                    if st.button("✅ Yes", key=f"confirm_{config_id}"):
                                        try:
                                            delete_response = requests.delete(
                                                f"{API_URL}/api/openai-config/{model_name}",
                                                timeout=10
                                            )
                                            if delete_response.status_code == 200:
                                                st.success("✅ Config deleted!")
                                                st.session_state[delete_confirm_key] = False
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error(f"Failed to delete: {delete_response.text}")
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")
                                with col_confirm2:
                                    if st.button("❌ Cancel", key=f"cancel_{config_id}"):
                                        st.session_state[delete_confirm_key] = False
                                        st.rerun()
                            else:
                                if st.button("🗑️ Delete", key=f"delete_{config_id}"):
                                    st.session_state[delete_confirm_key] = True
                                    st.rerun()
                        
                        st.markdown("---")
        else:
            st.error(f"Failed to load configs: {response.text}")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")

# ===== CREATE/EDIT CONFIG =====
if st.session_state.view_mode in ["create", "edit"]:
    # Determine if editing or creating
    is_editing = (st.session_state.view_mode == "edit" and st.session_state.edit_config is not None)
    
    if is_editing:
        st.subheader("✏️ Edit Model Configuration")
        edit_config = st.session_state.edit_config
        default_model = edit_config.get("model_name", "")
        default_input = edit_config.get("input_price_per_1m", 0) * 1_000_000  # Convert to per 1M for input
        default_output = edit_config.get("output_price_per_1m", 0) * 1_000_000
        default_active = edit_config.get("is_active", True)
        default_description = edit_config.get("description", "")
        default_provider = edit_config.get("provider", "openai")
        default_api_key = edit_config.get("api_key", "") or ""
        default_base_url = edit_config.get("base_url", "") or ""
    else:
        st.subheader("➕ Create Model Configuration")
        default_model = ""
        default_input = 0.150  # gpt-4o-mini default
        default_output = 0.600
        default_active = True
        default_description = ""
        default_provider = "openai"
        default_api_key = ""
        default_base_url = ""
    
    # Back button
    if st.button("← Back to List"):
        st.session_state.view_mode = "list"
        st.session_state.edit_config = None
        st.rerun()
    
    with st.form("config_form"):
        model_name = st.text_input(
            "Model Name",
            value=default_model,
            placeholder="gpt-4o-mini",
            disabled=is_editing,
            help="Name of the LLM model (e.g., gpt-4o-mini, gemini-1.5-pro, claude-3-sonnet)"
        )

        provider = st.selectbox(
            "Provider",
            options=["openai", "google", "anthropic", "groq"],
            index=["openai", "google", "anthropic", "groq"].index(default_provider if default_provider in ["openai", "google", "anthropic", "groq"] else "openai"),
            help="Chọn nhà cung cấp LLM"
        )
        
        st.markdown("**Pricing (per 1M tokens)**")
        col1, col2 = st.columns(2)
        
        with col1:
            input_price = st.number_input(
                "Input Price (per 1M tokens)",
                min_value=0.0,
                value=float(default_input),
                step=0.001,
                format="%.3f",
                help="Price per 1M input tokens in USD (e.g., 0.150 for $0.150/1M)"
            )
        
        with col2:
            output_price = st.number_input(
                "Output Price (per 1M tokens)",
                min_value=0.0,
                value=float(default_output),
                step=0.001,
                format="%.3f",
                help="Price per 1M output tokens in USD (e.g., 0.600 for $0.600/1M)"
            )
        
        # Convert back to per token for storage
        input_price_per_1m = input_price / 1_000_000
        output_price_per_1m = output_price / 1_000_000
        
        # Display calculated prices per token
        st.info(f"**Per token pricing:** Input: ${input_price_per_1m:.9f}, Output: ${output_price_per_1m:.9f}")
        
        is_active = st.checkbox("Active", value=default_active)
        
        description = st.text_area(
            "Description (optional)",
            value=default_description,
            placeholder="Brief description of this model configuration"
        )

        api_key = st.text_input(
            "API Key (optional, stored per config)",
            value=default_api_key,
            type="password",
            help="Nếu để trống sẽ dùng API key mặc định từ environment"
        )

        base_url = st.text_input(
            "Base URL (optional)",
            value=default_base_url,
            placeholder="https://api.groq.com/openai/v1",
            help="Dùng cho endpoint custom (Groq, Together, ...). Để trống nếu không cần."
        )
        
        submitted = st.form_submit_button(
            "✅ Save Config" if is_editing else "✅ Create Config",
            type="primary"
        )
        
        if submitted:
            if not model_name:
                st.error("Model name is required")
            elif input_price <= 0:
                st.error("Input price must be greater than 0")
            elif output_price <= 0:
                st.error("Output price must be greater than 0")
            else:
                try:
                    payload = {
                        "model_name": model_name,
                        "input_price_per_1m": input_price_per_1m,
                        "output_price_per_1m": output_price_per_1m,
                        "is_active": is_active,
                        "description": description if description else None,
                        "provider": provider,
                        "api_key": api_key or None,
                        "base_url": base_url or None,
                    }
                    
                    if is_editing:
                        # Update existing config
                        # Use spinner to block UI until save completes
                        with st.spinner("💾 Saving configuration..."):
                            try:
                                update_response = requests.put(
                                    f"{API_URL}/api/openai-config/{model_name}",
                                    json={
                                        "input_price_per_1m": input_price_per_1m,
                                        "output_price_per_1m": output_price_per_1m,
                                        "is_active": is_active,
                                        "description": description if description else None
                                    },
                                    timeout=30  # Increased timeout
                                )
                                # Wait for response before proceeding
                                response_status = update_response.status_code
                            except Exception as api_error:
                                st.error(f"Error calling API: {str(api_error)}")
                                response_status = None
                        
                        # Only proceed after API response is received and confirmed successful
                        if response_status == 200:
                            # Save successful - return to list
                            st.success("✅ Config updated successfully!")
                            # Clear edit state and return to list
                            st.session_state.edit_config = None
                            st.session_state.view_mode = "list"
                            # Brief delay to show success message, then rerun to switch view
                            time.sleep(0.5)
                            st.rerun()
                        elif response_status:
                            # Save failed - stay on current tab and show error
                            st.error(f"Failed to update config: {update_response.text}")
                        # If response_status is None, error already shown above
                    else:
                        # Create new config - use spinner to ensure save completes
                        with st.spinner("💾 Creating configuration, please wait..."):
                            try:
                                create_response = requests.post(
                                    f"{API_URL}/api/openai-config",
                                    json=payload,
                                    timeout=30
                                )
                                response_ok = create_response.status_code == 200
                            except Exception as e:
                                st.error(f"Error creating configuration: {str(e)}")
                                response_ok = False
                                create_response = None
                        
                        # Only return to list AFTER save is confirmed successful
                        if response_ok:
                            st.success("✅ Config created successfully!")
                            st.balloons()
                            # Clear form state and return to list
                            st.session_state.edit_config = None
                            st.session_state.view_mode = "list"
                            time.sleep(0.3)  # Brief delay to show success message and balloons
                            st.rerun()
                        elif create_response:
                            st.error(f"Failed to create config: {create_response.text}")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Footer info
st.markdown("---")

# Display current default model
try:
    default_response = requests.get(f"{API_URL}/api/openai-config/default-model", timeout=5)
    if default_response.status_code == 200:
        default_info = default_response.json()
        default_model = default_info.get("default_model", "gpt-4o-mini")
        from_db = default_info.get("from_db", False)
        source = "Database" if from_db else "Config"
        st.info(f"💡 **Current Default Model:** {default_model} (from {source})")
except:
    pass

st.info("💡 **Tip:** Use 'Sync Default Pricing' to populate default pricing for all providers. Edit individual models to customize pricing as needed. Click 'Set Default' to set a model as the default for AI calls.")

