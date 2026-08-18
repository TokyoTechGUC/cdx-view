export interface VariableStats {
    name: string;
    vmin: number;
    vmax: number;
    units: string | null;
    long_name: string | null;
    times: string[] | null;
    colormap: string | null;
}

export interface Dataset {
    id: string;
    name: string;
    description: string | null;
    variables: VariableStats[];
    format: 'zarr' | 'cog';
}

export interface ProjectSummary {
    id: string;
    title: string;
    description: string | null;
}

export interface ProjectDetail {
    id: string;
    title: string;
    description: string | null;
    datasets: Dataset[];
    background_layers: Dataset[];
}

// TODO: deprecate once registry preprocesses times into VariableStats.
export interface DatasetInfo {
    times?: string[];
}
