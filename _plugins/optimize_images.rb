# Optimize HTML output after every build, including jekyll serve regenerations.
require "open3"

Jekyll::Hooks.register :site, :post_write do |site|
  script = File.join(site.source, "scripts", "optimize_images.py")
  next unless File.file?(script)

  output, status = Open3.capture2e(
    ENV.fetch("IMAGE_PYTHON", "python3"), script,
    "--source", site.source,
    "--destination", site.dest,
    "--baseurl", site.baseurl.to_s
  )
  unless status.success?
    raise Jekyll::Errors::FatalException,
          "Image optimization failed. Install dependencies with " \
          "python3 -m pip install -r scripts/requirements.txt.\n#{output}"
  end
  Jekyll.logger.info output.strip
end
