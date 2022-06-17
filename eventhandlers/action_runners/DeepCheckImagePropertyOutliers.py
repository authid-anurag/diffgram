import cv2
from eventhandlers.action_runners.base.ActionRunner import ActionRunner
from deepchecks.vision.checks import ImagePropertyOutliers
from deepchecks.vision import VisionData

from skimage import io, transform
from sqlalchemy.orm import Session
from torch.utils.data import DataLoader
from io import BytesIO
from shared.database.source_control.working_dir import WorkingDir
from shared.database.source_control.working_dir import WorkingDirFileLink
from shared.helpers.sessionMaker import session_scope
from shared.database.source_control.file import File
from shared.database.project import Project
from shared.data_tools_core import Data_tools
from torch.utils.data import Dataset, DataLoader
import numpy as np

data_tools = Data_tools().data_tools


class DiffgramDataset(Dataset):
    def __init__(self, session: Session, diffgram_dir_id: int):
        self.session = session
        self.diffgram_dir_id = diffgram_dir_id
        query, count = WorkingDirFileLink.file_list(
            session = self.session,
            working_dir_id = self.diffgram_dir_id,
            type = ['image'],
            return_mode = "query",
            limit = None,
            order_by_class_and_attribute = File.id,
            count_before_limit = True
        )
        self.file_list = []
        for file in query.all():
            file.image.regenerate_url(session = self.session)
            self.file_list.append(file.serialize_with_type(session = self.session))
        self.count = count

    def __len__(self) -> int:
        return len(self.file_list)

    def __getitem__(self, idx: int) -> np.ndarray:
        file = self.file_list[idx]
        bytes_img = data_tools.download_bytes(file.get('image').get('url_signed_blob_path'))
        res = BytesIO(bytes_img)
        image = io.imread(res)
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return img


class DiffgramVisionDataset(VisionData):
    def batch_to_images(self, batch):
        """
        """
        return batch


class DeepcheckImagePropertyOutliers(ActionRunner):
    public_name = 'Deep Check - Image Properties Outliers'
    description = 'Image Properties Outliers'
    icon = 'https://finder.startupnationcentral.org/image_cloud/deepchecks_22b0d93d-3797-11ea-aa4a-bd6ae2b3f19f?w=240&h=240'
    kind = 'deep_checks__image_properties_outliers'  # The kind has to be unique to all actions
    category = 'Training Data Checks'  # Optional
    trigger_data = {'trigger_event_name': 'input_file_uploaded'}  # What events can this action listen to?
    condition_data = {'event_name': None}  # What pre-conditions can this action have?
    completion_condition_data = {
        'event_name': 'action_completed'}  # What options are available to declare the actions as completed?

    def execute_pre_conditions(self, session, action) -> bool:
        # Return true if no pre-conditions are needed.
        return True

    def execute_action(self, session):
        # Your core Action logic will go here.
        dir_id = self.event_data.get('directory_id')
        pytorch_dataset = DiffgramDataset(session = session, diffgram_dir_id = dir_id)
        dataloader = DataLoader(pytorch_dataset, batch_size = 100, shuffle = True, num_workers = 2,
                                collate_fn = lambda data: data)
        vision_ds = DiffgramVisionDataset(data_loader = dataloader)
        check = ImagePropertyOutliers()
        result = check.run(vision_ds)