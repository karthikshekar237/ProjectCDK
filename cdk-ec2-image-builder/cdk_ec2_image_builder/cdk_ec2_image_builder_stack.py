from aws_cdk import (
    aws_imagebuilder as imagebuilder,
    aws_codebuild as codebuild,
    aws_s3 as s3,
    aws_iam as iam,
    core
)
from aws_cdk.aws_s3_assets import Asset
import os

class CdkEc2ImageBuilderStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # S3 bucket to store build artifacts
        bucket = s3.Bucket(self, "BuildArtifactsBucket")
        
        # IAM role for CodeBuild
        codebuild_role = iam.Role(self, "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("EC2InstanceProfileForImageBuilder")
            ]
        )
        
        # CodeBuild project
        codebuild_project = codebuild.Project(self, "SOEImageBuilderProject",
            source=codebuild.Source.git_hub(
                owner="your-github-username",
                repo="your-github-repo",
                webhook=True, # optional, to trigger on new commits
            ),
            role=codebuild_role,
            artifacts=codebuild.Artifacts.s3(bucket=bucket),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0
            )
        )
        
        # Upload component definition file to S3
        nginx_component_asset = Asset(self, "NginxComponentAsset",
            path=os.path.join(os.path.dirname(__file__), "imagebuilder_components/install_nginx.yml")
        )

        # Image Builder component
        nginx_component = imagebuilder.CfnComponent(self, "NginxComponent",
            name="InstallNginx",
            platform="Linux",
            version="1.0.0",
            uri=nginx_component_asset.s3_object_url
        )
        
        # Image Builder infrastructure
        infrastructure_configuration = imagebuilder.CfnInfrastructureConfiguration(self, "InfrastructureConfiguration",
            name="MyInfrastructureConfiguration",
            instance_profile_name="EC2InstanceProfileForImageBuilder",
            subnet_id="subnet-xxxxxxxx",  # Replace with your subnet ID
            security_group_ids=["sg-xxxxxxxx"]  # Replace with your security group ID
        )
        
        # Image Recipe
        image_recipe = imagebuilder.CfnImageRecipe(self, "ImageRecipe",
            name="MySOEImageRecipe",
            version="1.0.0",
            components=[
                imagebuilder.CfnImageRecipe.ComponentConfigurationProperty(
                    component_arn="arn:aws:imagebuilder:us-west-2:aws:component/amazon-linux-2-base-amazon-linux-2/"
                ),
                imagebuilder.CfnImageRecipe.ComponentConfigurationProperty(
                    component_arn=nginx_component.attr_arn
                )
            ],
            parent_image="arn:aws:imagebuilder:us-west-2:aws:image/amazon-linux-2-x86/x.x.x",  # Replace with the base image ARN
        )
        
        # Image Pipeline
        image_pipeline = imagebuilder.CfnImagePipeline(self, "ImagePipeline",
            name="MyImagePipeline",
            image_recipe_arn=image_recipe.attr_arn,
            infrastructure_configuration_arn=infrastructure_configuration.attr_arn,
            schedule=imagebuilder.CfnImagePipeline.ScheduleProperty(
                schedule_expression="cron(0 0 * * ? *)"
            )
        )

app = core.App()
CdkEc2ImageBuilderStack(app, "CdkEc2ImageBuilderStack")
app.synth()

