"""
Browser Fingerprint Randomizer
Randomizes canvas, WebGL, fonts to avoid fingerprinting
Based on research from anti-detect browsers
"""
import random
from typing import Dict


class FingerprintRandomizer:
    """
    Advanced fingerprint randomization
    Prevents detection via canvas/WebGL/font fingerprinting
    """
    
    @staticmethod
    def get_canvas_randomizer_script() -> str:
        """
        Canvas fingerprinting protection
        Adds noise to canvas.toDataURL() and canvas.getImageData()
        """
        return """
        (function() {
            // Canvas fingerprinting protection
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            
            // Add noise to toDataURL
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                const shift = Math.floor(Math.random() * 10) - 5;
                const canvas = this;
                const ctx = canvas.getContext('2d');
                
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += shift;     // R
                        imageData.data[i + 1] += shift; // G
                        imageData.data[i + 2] += shift; // B
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
                
                return originalToDataURL.apply(this, arguments);
            };
            
            // Add noise to getImageData
            CanvasRenderingContext2D.prototype.getImageData = function() {
                const imageData = originalGetImageData.apply(this, arguments);
                const shift = Math.floor(Math.random() * 10) - 5;
                
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] += shift;
                    imageData.data[i + 1] += shift;
                    imageData.data[i + 2] += shift;
                }
                
                return imageData;
            };
        })();
        """
    
    @staticmethod
    def get_webgl_randomizer_script() -> str:
        """
        WebGL fingerprinting protection
        Randomizes WebGL vendor and renderer
        """
        vendors = [
            'Google Inc.',
            'Intel Inc.',
            'NVIDIA Corporation',
            'AMD',
            'Apple Inc.'
        ]
        
        renderers = [
            'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)',
            'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)',
            'ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0)',
            'Intel(R) Iris(TM) Plus Graphics 640',
            'Apple M1',
        ]
        
        vendor = random.choice(vendors)
        renderer = random.choice(renderers)
        
        return f"""
        (function() {{
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) {{
                    return '{vendor}';
                }}
                if (parameter === 37446) {{
                    return '{renderer}';
                }}
                return getParameter.apply(this, arguments);
            }};
            
            // Same for WebGL2
            if (window.WebGL2RenderingContext) {{
                const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return '{vendor}';
                    }}
                    if (parameter === 37446) {{
                        return '{renderer}';
                    }}
                    return getParameter2.apply(this, arguments);
                }};
            }}
        }})();
        """
    
    @staticmethod
    def get_font_randomizer_script() -> str:
        """
        Font fingerprinting protection
        Adds random fonts to available fonts list
        """
        return """
        (function() {
            // Randomize available fonts
            const extraFonts = [
                'Arial', 'Verdana', 'Helvetica', 'Times New Roman',
                'Courier New', 'Georgia', 'Palatino', 'Garamond',
                'Bookman', 'Comic Sans MS', 'Trebuchet MS', 'Impact'
            ];
            
            // Shuffle randomly
            for (let i = extraFonts.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [extraFonts[i], extraFonts[j]] = [extraFonts[j], extraFonts[i]];
            }
            
            // Add to document.fonts
            const originalCheck = document.fonts.check;
            document.fonts.check = function(font) {
                const fontFamily = font.split(' ').pop().replace(/['"]/g, '');
                if (extraFonts.includes(fontFamily)) {
                    return true;
                }
                return originalCheck.apply(this, arguments);
            };
        })();
        """
    
    @staticmethod
    def get_timezone_randomizer_script() -> str:
        """
        Timezone consistency check
        Ensures timezone matches geolocation
        """
        return """
        (function() {
            // Override timezone to match geolocation
            const originalDateTimeFormat = Intl.DateTimeFormat;
            Intl.DateTimeFormat = function(...args) {
                if (args[0] === undefined) {
                    args[0] = 'pt-BR';
                }
                return new originalDateTimeFormat(...args);
            };
            
            // Override Date.prototype.getTimezoneOffset
            const originalOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {
                return 180; // UTC-3 (São Paulo)
            };
        })();
        """
    
    @staticmethod
    def get_screen_randomizer_script() -> str:
        """
        Screen properties randomization
        Adds slight variance to screen dimensions
        """
        width = random.randint(1900, 1920)
        height = random.randint(1060, 1080)
        avail_width = width - random.randint(0, 5)
        avail_height = height - random.randint(30, 50)
        color_depth = random.choice([24, 32])
        pixel_depth = color_depth
        
        return f"""
        (function() {{
            Object.defineProperty(screen, 'width', {{
                get: () => {width}
            }});
            Object.defineProperty(screen, 'height', {{
                get: () => {height}
            }});
            Object.defineProperty(screen, 'availWidth', {{
                get: () => {avail_width}
            }});
            Object.defineProperty(screen, 'availHeight', {{
                get: () => {avail_height}
            }});
            Object.defineProperty(screen, 'colorDepth', {{
                get: () => {color_depth}
            }});
            Object.defineProperty(screen, 'pixelDepth', {{
                get: () => {pixel_depth}
            }});
        }})();
        """
    
    @staticmethod
    def get_battery_randomizer_script() -> str:
        """
        Battery API randomization
        Prevents battery status fingerprinting
        """
        level = round(random.uniform(0.3, 1.0), 2)
        charging = random.choice([True, False])
        charging_time = 0 if charging else float('inf')
        discharging_time = float('inf') if charging else random.randint(3600, 14400)
        
        return f"""
        (function() {{
            if (navigator.getBattery) {{
                const originalGetBattery = navigator.getBattery;
                navigator.getBattery = function() {{
                    return Promise.resolve({{
                        level: {level},
                        charging: {str(charging).lower()},
                        chargingTime: {charging_time},
                        dischargingTime: {discharging_time},
                        addEventListener: function() {{}},
                        removeEventListener: function() {{}}
                    }});
                }};
            }}
        }})();
        """
    
    @staticmethod
    def get_hardware_concurrency_script() -> str:
        """
        Hardware concurrency randomization
        Randomizes CPU core count
        """
        cores = random.choice([4, 6, 8, 12, 16])
        
        return f"""
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {cores}
        }});
        """
    
    @staticmethod
    def get_connection_randomizer_script() -> str:
        """
        Network Information API randomization
        """
        effective_types = ['4g', 'wifi']
        downlinks = [10, 50, 100, 200]
        rtts = [50, 100, 150]
        
        effective_type = random.choice(effective_types)
        downlink = random.choice(downlinks)
        rtt = random.choice(rtts)
        
        return f"""
        (function() {{
            if (navigator.connection) {{
                Object.defineProperty(navigator.connection, 'effectiveType', {{
                    get: () => '{effective_type}'
                }});
                Object.defineProperty(navigator.connection, 'downlink', {{
                    get: () => {downlink}
                }});
                Object.defineProperty(navigator.connection, 'rtt', {{
                    get: () => {rtt}
                }});
            }}
        }})();
        """
    
    @staticmethod
    def get_full_stealth_script() -> str:
        """
        Get complete stealth script with all randomizations
        """
        return f"""
        {FingerprintRandomizer.get_canvas_randomizer_script()}
        {FingerprintRandomizer.get_webgl_randomizer_script()}
        {FingerprintRandomizer.get_font_randomizer_script()}
        {FingerprintRandomizer.get_timezone_randomizer_script()}
        {FingerprintRandomizer.get_screen_randomizer_script()}
        {FingerprintRandomizer.get_battery_randomizer_script()}
        {FingerprintRandomizer.get_hardware_concurrency_script()}
        {FingerprintRandomizer.get_connection_randomizer_script()}
        
        // Additional stealth
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined
        }});
        
        window.chrome = {{
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
            app: {{}}
        }};
        
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [1, 2, 3, 4, 5]
        }});
        
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['en-US', 'en', 'pt-BR', 'pt']
        }});
        
        // Permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission }}) :
                originalQuery(parameters)
        );
        
        // Media devices
        if (navigator.mediaDevices) {{
            Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {{
                value: () => Promise.resolve([
                    {{ deviceId: 'default', kind: 'audioinput', label: '', groupId: '' }},
                    {{ deviceId: 'default', kind: 'audiooutput', label: '', groupId: '' }},
                    {{ deviceId: 'default', kind: 'videoinput', label: '', groupId: '' }}
                ])
            }});
        }}
        """
