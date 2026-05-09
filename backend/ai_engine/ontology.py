"""
Architecture Domain Ontology
The core knowledge graph mapping skills → roles → domains
This is what makes ArchIQ architecture-aware instead of keyword-matching
"""

DOMAIN_ONTOLOGY = {
    "domains": {
        "performance_engineering": {
            "label": "Performance Engineering",
            "color": "#1D9E75",
            "skills": ["pmu", "performance_counters", "workload_profiling", "cache_analysis",
                       "memory_bandwidth", "benchmarking", "perf_tool", "vtune", "arm_ds",
                       "cycle_accurate_simulation", "ipc_analysis", "roofline_model"]
        },
        "architecture_validation": {
            "label": "Architecture Validation",
            "color": "#3B8BD4",
            "skills": ["post_silicon_validation", "pre_silicon_validation", "bist", "scan_chain",
                       "jtag", "silicon_bringup", "dft", "atpg", "fault_coverage",
                       "debug_methodology", "emulation", "fpga_prototype"]
        },
        "embedded_soc": {
            "label": "Embedded / SoC",
            "color": "#534AB7",
            "skills": ["amba_apb", "amba_axi", "amba_ahb", "rtos", "bare_metal",
                       "interrupt_handling", "dma", "memory_mapped_io", "hal",
                       "linker_scripts", "startup_code", "mpu", "mmu"]
        },
        "hw_sw_codesign": {
            "label": "HW/SW Co-design",
            "color": "#D85A30",
            "skills": ["hw_sw_interface", "device_drivers", "firmware", "bsp",
                       "cache_coherence", "memory_consistency", "iommu",
                       "heterogeneous_computing", "openmp", "opencl"]
        },
        "ai_accelerators": {
            "label": "AI Accelerators",
            "color": "#BA7517",
            "skills": ["systolic_array", "tensor_core", "dataflow_architecture",
                       "cuda", "hip", "mlir", "tvm", "onnx", "quantization",
                       "sparsity", "npu", "tpu", "neural_engine"]
        },
        "computer_architecture": {
            "label": "Computer Architecture",
            "color": "#993556",
            "skills": ["pipeline_design", "ooo_execution", "branch_prediction",
                       "cache_hierarchy", "tlb", "simd", "simt", "noc",
                       "memory_hierarchy", "register_file", "fetch_decode_execute",
                       "risc_v", "arm_architecture", "x86_architecture"]
        },
        "compiler_runtime": {
            "label": "Compiler / Runtime",
            "color": "#639922",
            "skills": ["llvm", "gcc", "code_generation", "register_allocation",
                       "instruction_scheduling", "vectorization", "loop_optimization",
                       "jit", "runtime_systems", "abi", "calling_conventions"]
        }
    },

    "skills": {
        # Performance
        "pmu": {"name": "PMU / Performance Monitoring Unit", "domain": "performance_engineering", "weight": 0.95},
        "performance_counters": {"name": "Hardware Performance Counters", "domain": "performance_engineering", "weight": 0.9},
        "workload_profiling": {"name": "Workload Profiling & Analysis", "domain": "performance_engineering", "weight": 0.88},
        "cache_analysis": {"name": "Cache Sensitivity Analysis", "domain": "performance_engineering", "weight": 0.85},
        "benchmarking": {"name": "Benchmarking & Microbenchmarks", "domain": "performance_engineering", "weight": 0.82},
        "ipc_analysis": {"name": "IPC / CPI Analysis", "domain": "performance_engineering", "weight": 0.80},

        # Arch validation
        "post_silicon_validation": {"name": "Post-Silicon Validation", "domain": "architecture_validation", "weight": 0.95},
        "bist": {"name": "BIST (Built-In Self-Test)", "domain": "architecture_validation", "weight": 0.88},
        "scan_chain": {"name": "Scan Chain / DFT", "domain": "architecture_validation", "weight": 0.85},
        "jtag": {"name": "JTAG Debugging", "domain": "architecture_validation", "weight": 0.80},
        "silicon_bringup": {"name": "Silicon Bring-up", "domain": "architecture_validation", "weight": 0.92},
        "dft": {"name": "Design for Testability", "domain": "architecture_validation", "weight": 0.87},
        "atpg": {"name": "ATPG", "domain": "architecture_validation", "weight": 0.82},

        # SoC / Embedded
        "amba_apb": {"name": "AMBA APB Protocol", "domain": "embedded_soc", "weight": 0.85},
        "amba_axi": {"name": "AMBA AXI Protocol", "domain": "embedded_soc", "weight": 0.88},
        "rtos": {"name": "RTOS / Real-Time OS", "domain": "embedded_soc", "weight": 0.80},
        "bare_metal": {"name": "Bare-metal Embedded", "domain": "embedded_soc", "weight": 0.82},
        "linker_scripts": {"name": "Linker Scripts & Memory Maps", "domain": "embedded_soc", "weight": 0.75},
        "mpu": {"name": "MPU / Memory Protection Unit", "domain": "embedded_soc", "weight": 0.78},

        # Architecture
        "ooo_execution": {"name": "Out-of-Order Execution", "domain": "computer_architecture", "weight": 0.92},
        "branch_prediction": {"name": "Branch Prediction", "domain": "computer_architecture", "weight": 0.85},
        "cache_hierarchy": {"name": "Cache Hierarchy Design", "domain": "computer_architecture", "weight": 0.88},
        "simd": {"name": "SIMD / Vector Processing", "domain": "computer_architecture", "weight": 0.82},
        "simt": {"name": "SIMT (GPU threading)", "domain": "computer_architecture", "weight": 0.85},
        "risc_v": {"name": "RISC-V Architecture", "domain": "computer_architecture", "weight": 0.90},
        "noc": {"name": "Network-on-Chip (NoC)", "domain": "computer_architecture", "weight": 0.85},

        # AI accelerators
        "systolic_array": {"name": "Systolic Array Architecture", "domain": "ai_accelerators", "weight": 0.90},
        "tensor_core": {"name": "Tensor Core / Matrix Unit", "domain": "ai_accelerators", "weight": 0.88},
        "cuda": {"name": "CUDA Programming", "domain": "ai_accelerators", "weight": 0.85},
        "quantization": {"name": "Model Quantization", "domain": "ai_accelerators", "weight": 0.80},
        "mlir": {"name": "MLIR Compiler Framework", "domain": "ai_accelerators", "weight": 0.88},
        "dataflow_architecture": {"name": "Dataflow Architecture", "domain": "ai_accelerators", "weight": 0.90},

        # HW/SW
        "device_drivers": {"name": "Device Driver Development", "domain": "hw_sw_codesign", "weight": 0.85},
        "cache_coherence": {"name": "Cache Coherence Protocols", "domain": "hw_sw_codesign", "weight": 0.88},
        "memory_consistency": {"name": "Memory Consistency Models", "domain": "hw_sw_codesign", "weight": 0.85},
        "firmware": {"name": "Firmware Development", "domain": "hw_sw_codesign", "weight": 0.82},
    },

    "roles": {
        "architecture_validation_engineer": {
            "label": "Architecture Validation Engineer",
            "primary_skills": ["post_silicon_validation", "bist", "scan_chain", "pmu", "jtag", "silicon_bringup"],
            "secondary_skills": ["dft", "atpg", "ooo_execution", "cache_hierarchy", "risc_v"],
            "companies": ["Intel", "AMD", "ARM", "NVIDIA", "Qualcomm", "Apple", "Amazon"]
        },
        "performance_engineer": {
            "label": "Performance Engineer",
            "primary_skills": ["pmu", "workload_profiling", "benchmarking", "cache_analysis", "ipc_analysis"],
            "secondary_skills": ["ooo_execution", "cache_hierarchy", "simd", "risc_v", "roofline_model"],
            "companies": ["Intel", "AMD", "ARM", "NVIDIA", "Google", "Meta", "Apple", "Tenstorrent"]
        },
        "ai_accelerator_engineer": {
            "label": "AI Accelerator Engineer",
            "primary_skills": ["systolic_array", "tensor_core", "dataflow_architecture", "cuda", "mlir"],
            "secondary_skills": ["simt", "cache_hierarchy", "noc", "quantization", "memory_consistency"],
            "companies": ["NVIDIA", "Google", "Tenstorrent", "Cerebras", "Groq", "AWS Annapurna", "Apple"]
        },
        "soc_engineer": {
            "label": "SoC Engineer",
            "primary_skills": ["amba_axi", "amba_apb", "noc", "cache_coherence", "mpu"],
            "secondary_skills": ["rtos", "dma", "linker_scripts", "bist", "dft"],
            "companies": ["Qualcomm", "MediaTek", "ARM", "Broadcom", "NXP", "STMicroelectronics"]
        },
        "benchmarking_engineer": {
            "label": "Benchmarking Engineer",
            "primary_skills": ["benchmarking", "workload_profiling", "pmu", "ipc_analysis", "cache_analysis"],
            "secondary_skills": ["risc_v", "cache_hierarchy", "ooo_execution"],
            "companies": ["SPEC", "ARM", "Intel", "AMD", "Google", "Qualcomm"]
        },
        "hw_sw_codesign_engineer": {
            "label": "HW/SW Co-design Engineer",
            "primary_skills": ["device_drivers", "cache_coherence", "memory_consistency", "firmware", "hw_sw_interface"],
            "secondary_skills": ["amba_axi", "rtos", "pmu", "mmu", "opencl"],
            "companies": ["ARM", "Intel", "AMD", "NVIDIA", "Xilinx/AMD", "Lattice"]
        },
        "embedded_systems_engineer": {
            "label": "Embedded Systems Engineer",
            "primary_skills": ["bare_metal", "rtos", "amba_apb", "linker_scripts", "mpu", "firmware"],
            "secondary_skills": ["device_drivers", "jtag", "bist", "dma"],
            "companies": ["Bosch", "NXP", "STMicro", "TI", "Microchip", "Renesas", "Nordic"]
        }
    },

    "skill_relations": [
        {"from": "pmu", "to": "performance_counters", "type": "enables"},
        {"from": "performance_counters", "to": "workload_profiling", "type": "enables"},
        {"from": "workload_profiling", "to": "cache_analysis", "type": "enables"},
        {"from": "cache_analysis", "to": "ooo_execution", "type": "related"},
        {"from": "bist", "to": "scan_chain", "type": "requires"},
        {"from": "scan_chain", "to": "dft", "type": "related"},
        {"from": "dft", "to": "atpg", "type": "enables"},
        {"from": "amba_apb", "to": "amba_axi", "type": "progression"},
        {"from": "amba_axi", "to": "noc", "type": "related"},
        {"from": "risc_v", "to": "ooo_execution", "type": "context"},
        {"from": "ooo_execution", "to": "cache_hierarchy", "type": "related"},
        {"from": "cache_hierarchy", "to": "cache_coherence", "type": "enables"},
        {"from": "simt", "to": "systolic_array", "type": "related"},
        {"from": "cuda", "to": "tensor_core", "type": "enables"},
    ],

    "depth_levels": {
        "awareness": {"label": "Awareness", "score": 1, "color": "#888780"},
        "implementation": {"label": "Implementation", "score": 2, "color": "#3B8BD4"},
        "optimization": {"label": "Optimization", "score": 3, "color": "#1D9E75"},
        "architecture_reasoning": {"label": "Arch Reasoning", "score": 4, "color": "#534AB7"},
        "production_exposure": {"label": "Production Exposure", "score": 5, "color": "#D85A30"}
    }
}

TARGET_COMPANIES = [
    {"name": "NVIDIA", "careers_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"},
    {"name": "AMD", "careers_url": "https://careers.amd.com/careers-home/jobs"},
    {"name": "Intel", "careers_url": "https://jobs.intel.com/en/search-jobs"},
    {"name": "ARM", "careers_url": "https://careers.arm.com/en/jobs"},
    {"name": "Qualcomm", "careers_url": "https://careers.qualcomm.com/careers"},
    {"name": "Tenstorrent", "careers_url": "https://tenstorrent.com/careers"},
    {"name": "Bosch", "careers_url": "https://www.bosch.com/careers/jobs"},
    {"name": "NXP", "careers_url": "https://nxp.wd3.myworkdayjobs.com/careers"},
    {"name": "MediaTek", "careers_url": "https://careers.mediatek.com/eREC/JobSearch/Search"},
    {"name": "Cerebras", "careers_url": "https://www.cerebras.net/careers"},
]

ARCH_KEYWORDS = [
    "PMU", "performance monitoring", "workload profiling", "cache analysis",
    "post-silicon", "pre-silicon", "silicon validation", "bringup", "bring-up",
    "BIST", "scan chain", "DFT", "ATPG", "JTAG",
    "AMBA", "AXI", "APB", "AHB", "SoC", "embedded",
    "RISC-V", "ARM", "microarchitecture", "pipeline", "out-of-order",
    "benchmarking", "IPC", "CPI", "roofline",
    "AI accelerator", "systolic", "tensor core", "CUDA", "dataflow",
    "cache coherence", "memory consistency", "device driver",
    "compiler", "LLVM", "MLIR", "runtime",
    "NoC", "SIMD", "SIMT", "branch prediction"
]
