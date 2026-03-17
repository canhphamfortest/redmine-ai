module CustomFeatures
  module Hooks
    require 'set'

    # View hooks để inject HTML vào các view của Redmine
    # Sử dụng Redmine hook system để thêm custom features vào UI
    class ViewHooks < Redmine::Hook::ViewListener
      # Hook vào sau phần details của issue show page
      # Hiển thị custom related issues section với các button tùy chỉnh
      # Hook point này tồn tại trong mọi phiên bản Redmine
      #
      # @param context [Hash] Context từ Redmine hook, chứa:
      #   - :issue [Issue] Issue object đang được hiển thị
      #   - :controller [ApplicationController] Controller instance
      # @return [String] HTML string để inject vào view, hoặc '' nếu có lỗi
      def view_issues_show_details_bottom(context = {})
        issue = context[:issue]
        return '' unless issue
        
        controller = context[:controller]
        controller.render_to_string(
          partial: 'custom_features/hooks/view_issues_related_custom',
          locals: { issue: issue }
        )
      rescue => e
        Rails.logger.error "CustomFeatures hook error: #{e.message}"
        ''
      end


      # Hook để thêm CSS và JS vào <head> của layout
      # Load các assets (CSS, JavaScript) của plugin vào mọi trang
      # Trong Redmine, plugin assets được serve từ /plugin_assets/{plugin_name}/
      # Sử dụng cách tạo HTML string trực tiếp để tránh lỗi với helper methods
      #
      # Load order cho JavaScript:
      # 1. utils.js (utility functions)
      # 2. search.js (search functionality)
      # 3. checklist.js (checklist functionality)
      # 4. auto_link.js (auto-link functionality)
      # 5. main.js (main initialization)
      #
      # @param context [Hash] Context từ Redmine hook (không sử dụng trong method này)
      # @return [String] HTML string chứa <link> và <script> tags, hoặc '' nếu có lỗi
      def view_layouts_base_html_head(context = {})
        plugin_name = 'custom_features'
        plugin_assets_path = "/plugin_assets/#{plugin_name}"
        enabled_projects = expand_enabled_projects(Setting.plugin_custom_features['enabled_projects'] || [])
        
        # CSS
        css_tag = %Q{<link href="#{plugin_assets_path}/stylesheets/custom_features.css" rel="stylesheet" type="text/css" />}
        
        # Các module JavaScript (load theo thứ tự: utils trước, sau đó các module tính năng, cuối cùng là main)
        js_modules = [
          'custom_features/utils.js',
          'custom_features/search.js',
          'custom_features/checklist.js',
          'custom_features/auto_link.js',
          'custom_features/main.js'
        ]
        
        js_tags = js_modules.map do |js_file|
          %Q{<script src="#{plugin_assets_path}/javascripts/#{js_file}" type="text/javascript"></script>}
        end.join("\n")

        config_tag = %Q{
          <script type="text/javascript">
            window.CustomFeaturesEnabledProjects = #{enabled_projects.to_json};
          </script>
        }

        css_tag + "\n" + js_tags + "\n" + config_tag
      rescue => e
        Rails.logger.error "CustomFeatures assets error: #{e.message}"
        ''
      end

      private

      # Mở rộng danh sách project được bật: nếu chọn parent thì tự động bao gồm tất cả subprojects
      def expand_enabled_projects(project_identifiers)
        identifiers = Array(project_identifiers).reject(&:blank?)
        return [] if identifiers.empty?

        identifiers_set = Set.new(identifiers)
        projects = Project.where(identifier: identifiers)
        projects.each { |project| collect_descendant_identifiers(project, identifiers_set) }

        identifiers_set.to_a
      rescue StandardError => e
        Rails.logger.error "CustomFeatures expand_enabled_projects error: #{e.message}"
        project_identifiers
      end

      def collect_descendant_identifiers(project, identifiers_set)
        return unless project.respond_to?(:descendants)

        project.descendants.each do |child|
          identifiers_set << child.identifier
        end
      end
    end
  end
end

